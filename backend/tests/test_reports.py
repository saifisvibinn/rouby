from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch, Location
from app.models.catalog import Ingredient, ProductVariant
from app.models.inventory import InventoryBalance
from app.models.sales import SaleItemConsumption
from app.models.user import User
from app.services.inventory_service import InventoryService
from app.services.report_service import ReportService
from app.services.sales_service import SalesService


async def _ingredient(session: AsyncSession, sku: str) -> Ingredient:
    result = await session.execute(select(Ingredient).where(Ingredient.sku == sku))
    return result.scalar_one()


async def _location(session: AsyncSession, code: str) -> Location:
    result = await session.execute(select(Location).where(Location.code == code))
    return result.scalar_one()


async def _user(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == "admin@rouby.app"))
    return result.scalar_one()


async def _branch(session: AsyncSession) -> Branch:
    result = await session.execute(select(Branch).where(Branch.code == "MAIN"))
    return result.scalar_one()


async def _variant_by_sku(session: AsyncSession, sku: str) -> ProductVariant:
    result = await session.execute(select(ProductVariant).where(ProductVariant.sku == sku))
    return result.scalar_one()


async def _balance_for(
    session: AsyncSession,
    ingredient_id: UUID,
    location_id: UUID,
) -> InventoryBalance | None:
    result = await session.execute(
        select(InventoryBalance).where(
            InventoryBalance.ingredient_id == ingredient_id,
            InventoryBalance.location_id == location_id,
        )
    )
    return result.scalar_one_or_none()


async def _boost_stock(
    session: AsyncSession,
    sku: str,
    location_code: str,
    target_qty: Decimal,
) -> None:
    ingredient = await _ingredient(session, sku)
    location = await _location(session, location_code)
    balance = await _balance_for(session, ingredient.id, location.id)
    current = Decimal(balance.qty_on_hand) if balance else Decimal("0")
    if current >= target_qty:
        return

    await InventoryService(session).apply_purchase_receipt(
        ingredient_id=ingredient.id,
        location_id=location.id,
        received_qty=target_qty - current,
        unit_cost=ingredient.wac,
    )
    await session.flush()


async def _create_confirmed_sale(session: AsyncSession):
    await _boost_stock(session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(session, "BANANA", "DRY", Decimal("50"))
    await _boost_stock(session, "WHEY", "DRY", Decimal("100"))

    user = await _user(session)
    branch = await _branch(session)
    variant = await _variant_by_sku(session, "BANANA_PROTEIN_SHAKE")
    service = SalesService(session)
    sale = await service.create_sale(
        branch_id=branch.id,
        user_id=user.id,
        order_type="dine_in",
        items=[{"variant_id": variant.id, "qty": 2}],
    )
    return await service.confirm(sale.id, str(uuid4()), user_id=user.id)


@pytest.mark.asyncio
async def test_sales_report_total_matches_sum_of_sale_lines(
    db_session: AsyncSession,
) -> None:
    from_at = datetime.now(UTC) - timedelta(seconds=1)
    sale = await _create_confirmed_sale(db_session)
    to_at = datetime.now(UTC) + timedelta(seconds=1)

    report = await ReportService(db_session).sales_report(from_at=from_at, to_at=to_at)
    expected_total = sum((Decimal(item.line_total) for item in sale.items), Decimal("0"))

    assert Decimal(report["totals"]["sales_total"]) == expected_total


@pytest.mark.asyncio
async def test_profit_report_cogs_matches_consumption_snapshots(
    db_session: AsyncSession,
) -> None:
    from_at = datetime.now(UTC) - timedelta(seconds=1)
    sale = await _create_confirmed_sale(db_session)
    to_at = datetime.now(UTC) + timedelta(seconds=1)

    report = await ReportService(db_session).profit_report(from_at=from_at, to_at=to_at)
    sale_item_ids = [item.id for item in sale.items]
    result = await db_session.execute(
        select(SaleItemConsumption).where(SaleItemConsumption.sale_item_id.in_(sale_item_ids))
    )
    expected_cogs = sum(
        (Decimal(consumption.line_cogs) for consumption in result.scalars().all()),
        Decimal("0"),
    )

    assert Decimal(report["totals"]["cogs"]) == expected_cogs

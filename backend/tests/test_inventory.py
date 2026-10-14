from datetime import date
from decimal import Decimal

import pytest
from app.models.branch import Location
from app.models.catalog import Ingredient
from app.models.inventory import (
    InventoryBalance,
    InventoryBatch,
    PurchaseOrder,
    StockCountItem,
    StockMovement,
)
from app.services.inventory_service import InventoryService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _ingredient(session: AsyncSession, sku: str) -> Ingredient:
    result = await session.execute(select(Ingredient).where(Ingredient.sku == sku))
    return result.scalar_one()


async def _location(session: AsyncSession, code: str) -> Location:
    result = await session.execute(select(Location).where(Location.code == code))
    return result.scalar_one()


async def _balance(
    session: AsyncSession,
    ingredient: Ingredient,
    location: Location,
) -> InventoryBalance:
    result = await session.execute(
        select(InventoryBalance).where(
            InventoryBalance.ingredient_id == ingredient.id,
            InventoryBalance.location_id == location.id,
        )
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_purchase_order_does_not_change_stock_then_receipt_updates_wac(
    db_session: AsyncSession,
) -> None:
    milk = await _ingredient(db_session, "MILK")
    fridge = await _location(db_session, "FRIDGE")
    service = InventoryService(db_session)
    before = await _balance(db_session, milk, fridge)
    old_qty = Decimal(before.qty_on_hand)
    old_wac = Decimal(milk.wac)

    order = await service.create_purchase_order(
        branch_id=fridge.branch_id,
        supplier_id=milk.default_supplier_id,
        items=[
            {
                "ingredient_id": milk.id,
                "ordered_qty": Decimal("10000"),
                "unit_cost": Decimal("0.09"),
            }
        ],
    )
    assert isinstance(order, PurchaseOrder)
    unchanged = await _balance(db_session, milk, fridge)
    assert unchanged.qty_on_hand == Decimal("3000.000")

    await service.apply_purchase_receipt(
        ingredient_id=milk.id,
        location_id=fridge.id,
        received_qty=Decimal("10000"),
        unit_cost=Decimal("0.09"),
    )
    after = await _balance(db_session, milk, fridge)
    await db_session.refresh(milk)

    assert old_qty == Decimal("3000.000")
    assert after.qty_on_hand == Decimal("13000.000")
    expected_wac = ((old_qty * old_wac) + (Decimal("10000") * Decimal("0.09"))) / Decimal("13000")
    assert milk.wac == expected_wac.quantize(Decimal("0.000001"))


@pytest.mark.asyncio
async def test_waste_bananas_reduces_balance_and_writes_ledger(db_session: AsyncSession) -> None:
    banana = await _ingredient(db_session, "BANANA")
    dry = await _location(db_session, "DRY")

    record = await InventoryService(db_session).apply_waste(
        ingredient_id=banana.id,
        location_id=dry.id,
        quantity_base=Decimal("3"),
        reason="Bruised",
    )
    balance = await _balance(db_session, banana, dry)
    movement = await db_session.get(StockMovement, record.movement_id)

    assert balance.qty_on_hand == Decimal("17.000")
    assert movement is not None
    assert movement.type == "WASTE"
    assert movement.quantity_base == Decimal("-3.000")


@pytest.mark.asyncio
async def test_stock_count_posts_count_variance(db_session: AsyncSession) -> None:
    chicken = await _ingredient(db_session, "CHICKEN")
    fridge = await _location(db_session, "FRIDGE")
    service = InventoryService(db_session)

    count = await service.create_stock_count(
        location_id=fridge.id,
        items=[{"ingredient_id": chicken.id, "actual_qty": Decimal("2700")}],
    )
    posted = await service.post_stock_count_variance(count.id)
    item = (await db_session.execute(select(StockCountItem))).scalars().first()
    movement = await db_session.get(StockMovement, item.movement_id)
    balance = await _balance(db_session, chicken, fridge)

    assert posted.status == "POSTED"
    assert item.theoretical_qty == Decimal("3000.000")
    assert item.variance_qty == Decimal("-300.000")
    assert movement is not None
    assert movement.type == "COUNT_VARIANCE"
    assert movement.quantity_base == Decimal("-300.000")
    assert balance.qty_on_hand == Decimal("2700.000")


@pytest.mark.asyncio
async def test_fefo_picks_earliest_expiry_batch(db_session: AsyncSession) -> None:
    strawberry = await _ingredient(db_session, "STRAWBERRY")
    fridge = await _location(db_session, "FRIDGE")
    service = InventoryService(db_session)

    await service.apply_purchase_receipt(
        ingredient_id=strawberry.id,
        location_id=fridge.id,
        received_qty=Decimal("5"),
        unit_cost=Decimal("0.20"),
        expiry_date=date(2026, 11, 1),
    )
    await service.apply_purchase_receipt(
        ingredient_id=strawberry.id,
        location_id=fridge.id,
        received_qty=Decimal("5"),
        unit_cost=Decimal("0.22"),
        expiry_date=date(2026, 10, 20),
    )

    allocations = await service.allocate_fefo(strawberry.id, fridge.id, Decimal("7"))
    batches = (
        await db_session.execute(
            select(InventoryBatch)
            .where(InventoryBatch.ingredient_id == strawberry.id)
            .order_by(InventoryBatch.expiry_date.asc())
        )
    ).scalars().all()

    assert allocations[0].quantity == Decimal("5.000")
    assert batches[0].expiry_date == date(2026, 10, 20)
    assert batches[0].remaining_qty == Decimal("0.000")
    assert batches[1].remaining_qty == Decimal("3.000")


@pytest.mark.asyncio
async def test_ledger_rebuild_equals_balances_after_random_ops(db_session: AsyncSession) -> None:
    milk = await _ingredient(db_session, "MILK")
    fridge = await _location(db_session, "FRIDGE")
    banana = await _ingredient(db_session, "BANANA")
    dry = await _location(db_session, "DRY")
    service = InventoryService(db_session)

    await service.apply_adjustment(
        ingredient_id=milk.id,
        location_id=fridge.id,
        quantity_delta=Decimal("125"),
        reason="Found sealed carton",
    )
    await service.apply_waste(
        ingredient_id=banana.id,
        location_id=dry.id,
        quantity_base=Decimal("2"),
        reason="Spoiled",
    )
    await service.apply_purchase_receipt(
        ingredient_id=banana.id,
        location_id=dry.id,
        received_qty=Decimal("12"),
        unit_cost=Decimal("11"),
    )

    rebuilt = await service.rebuild_balances_from_ledger()
    assert rebuilt[(milk.id, fridge.id)] == Decimal("3125.000")
    assert rebuilt[(banana.id, dry.id)] == Decimal("30.000")


@pytest.mark.asyncio
async def test_purchase_price_change_updates_wac_for_later_sales(db_session: AsyncSession) -> None:
    coffee = await _ingredient(db_session, "COFFEE_BEANS")
    dry = await _location(db_session, "DRY")
    service = InventoryService(db_session)
    balance = await _balance(db_session, coffee, dry)
    old_qty = Decimal(balance.qty_on_hand)
    old_wac = Decimal(coffee.wac)

    await service.apply_purchase_receipt(
        ingredient_id=coffee.id,
        location_id=dry.id,
        received_qty=Decimal("1000"),
        unit_cost=Decimal("1.20"),
    )
    await db_session.refresh(coffee)

    expected = ((old_qty * old_wac) + (Decimal("1000") * Decimal("1.20"))) / (
        old_qty + Decimal("1000")
    )
    assert coffee.wac == expected.quantize(Decimal("0.000001"))

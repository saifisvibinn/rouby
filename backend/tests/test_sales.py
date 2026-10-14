import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from app.core.errors import AppError
from app.models.branch import Branch, Location
from app.models.catalog import Ingredient, Modifier, ProductVariant
from app.models.inventory import InventoryBalance, StockMovement
from app.models.sales import Sale, SaleItemConsumption
from app.models.settings import Setting
from app.models.user import User
from app.services.inventory_service import InventoryService
from app.services.sales_service import SalesService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _ingredient(session: AsyncSession, sku: str) -> Ingredient:
    result = await session.execute(
        select(Ingredient).where(Ingredient.sku == sku)
    )
    return result.scalar_one()


async def _location(session: AsyncSession, code: str) -> Location:
    result = await session.execute(
        select(Location).where(Location.code == code)
    )
    return result.scalar_one()


async def _user(session: AsyncSession) -> User:
    result = await session.execute(
        select(User).where(User.email == "admin@rouby.app")
    )
    return result.scalar_one()


async def _branch(session: AsyncSession) -> Branch:
    result = await session.execute(
        select(Branch).where(Branch.code == "MAIN")
    )
    return result.scalar_one()


async def _variant_by_sku(
    session: AsyncSession, sku: str
) -> ProductVariant:
    result = await session.execute(
        select(ProductVariant).where(ProductVariant.sku == sku)
    )
    return result.scalar_one()


async def _modifier_by_code(
    session: AsyncSession, code: str
) -> Modifier:
    result = await session.execute(
        select(Modifier).where(Modifier.code == code)
    )
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
    if current < target_qty:
        needed = target_qty - current
        await InventoryService(session).apply_purchase_receipt(
            ingredient_id=ingredient.id,
            location_id=location.id,
            received_qty=needed,
            unit_cost=ingredient.wac,
        )
    await session.flush()


async def _set_policy(session: AsyncSession, value: str) -> None:
    result = await session.execute(
        select(Setting).where(Setting.key == "negative_stock_policy")
    )
    setting = result.scalar_one()
    setting.value = value
    await session.flush()


async def _create_and_confirm_shake(
    session: AsyncSession,
    *,
    modifier_ids: list[UUID] | None = None,
    qty: int = 1,
    idempotency_key: str | None = None,
) -> Sale:
    user = await _user(session)
    branch = await _branch(session)
    variant = await _variant_by_sku(session, "BANANA_PROTEIN_SHAKE")

    svc = SalesService(session)
    item_data: dict = {"variant_id": variant.id, "qty": qty}
    if modifier_ids:
        item_data["modifier_ids"] = modifier_ids

    sale = await svc.create_sale(
        branch_id=branch.id,
        user_id=user.id,
        order_type="dine_in",
        items=[item_data],
    )
    key = idempotency_key or str(uuid4())
    confirmed = await svc.confirm(sale.id, key, user_id=user.id)
    return confirmed


@pytest.mark.asyncio
async def test_sell_banana_protein_shake_deducts_stock_and_cogs(
    db_session: AsyncSession,
) -> None:
    """Test 1: Sell 1 Banana Protein Shake."""
    await _boost_stock(db_session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(db_session, "BANANA", "DRY", Decimal("50"))
    await _boost_stock(db_session, "WHEY", "DRY", Decimal("100"))

    milk = await _ingredient(db_session, "MILK")
    banana = await _ingredient(db_session, "BANANA")
    whey = await _ingredient(db_session, "WHEY")
    fridge = await _location(db_session, "FRIDGE")
    dry = await _location(db_session, "DRY")

    milk_before = await _balance_for(db_session, milk.id, fridge.id)
    banana_before = await _balance_for(db_session, banana.id, dry.id)
    whey_before = await _balance_for(db_session, whey.id, dry.id)

    assert milk_before.qty_on_hand == Decimal("20000.000")
    assert banana_before.qty_on_hand == Decimal("50.000")
    assert whey_before.qty_on_hand == Decimal("100.000")

    sale = await _create_and_confirm_shake(db_session)

    await db_session.refresh(milk_before)
    await db_session.refresh(banana_before)
    await db_session.refresh(whey_before)

    assert milk_before.qty_on_hand == Decimal("19800.000")
    assert banana_before.qty_on_hand == Decimal("49.000")
    assert whey_before.qty_on_hand == Decimal("99.000")

    assert sale.cogs_total == Decimal("62.00")
    expected_margin = (Decimal("120") - Decimal("62")) / Decimal("120") * 100
    assert expected_margin.quantize(Decimal("0.01")) == Decimal("48.33")
    assert sale.status == "CONFIRMED"


@pytest.mark.asyncio
async def test_sell_chicken_wraps_deducts_chicken(
    db_session: AsyncSession,
) -> None:
    """Test 2: Sell 10 Chicken Wraps."""
    await _boost_stock(db_session, "CHICKEN", "FRIDGE", Decimal("5000"))
    await _boost_stock(db_session, "TORTILLA", "DRY", Decimal("50"))
    await _boost_stock(db_session, "MOZZARELLA", "FRIDGE", Decimal("5000"))

    chicken = await _ingredient(db_session, "CHICKEN")
    fridge = await _location(db_session, "FRIDGE")
    chicken_before = await _balance_for(db_session, chicken.id, fridge.id)
    assert chicken_before.qty_on_hand == Decimal("5000.000")

    user = await _user(db_session)
    branch = await _branch(db_session)
    variant = await _variant_by_sku(db_session, "CHICKEN_WRAP")

    svc = SalesService(db_session)
    sale = await svc.create_sale(
        branch_id=branch.id,
        user_id=user.id,
        order_type="takeaway",
        items=[{"variant_id": variant.id, "qty": 10}],
    )
    confirmed = await svc.confirm(sale.id, str(uuid4()), user_id=user.id)

    await db_session.refresh(chicken_before)
    assert chicken_before.qty_on_hand == Decimal("4500.000")
    assert confirmed.status == "CONFIRMED"


@pytest.mark.asyncio
async def test_shake_double_whey_no_banana(
    db_session: AsyncSession,
) -> None:
    """Test 3: Banana Protein Shake with Double Whey + No Banana."""
    await _boost_stock(db_session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(db_session, "BANANA", "DRY", Decimal("50"))
    await _boost_stock(db_session, "WHEY", "DRY", Decimal("100"))

    double_whey = await _modifier_by_code(db_session, "DOUBLE_WHEY")
    no_banana = await _modifier_by_code(db_session, "NO_BANANA")

    sale = await _create_and_confirm_shake(
        db_session,
        modifier_ids=[double_whey.id, no_banana.id],
    )

    assert sale.items[0].unit_price == Decimal("160.00")
    assert sale.total == Decimal("160.00")

    consumptions = sale.items[0].consumptions
    consumption_map = {c.ingredient_id: c for c in consumptions}

    milk = await _ingredient(db_session, "MILK")
    whey = await _ingredient(db_session, "WHEY")
    banana = await _ingredient(db_session, "BANANA")

    assert milk.id in consumption_map
    assert consumption_map[milk.id].qty_base == Decimal("200.000")

    assert whey.id in consumption_map
    assert consumption_map[whey.id].qty_base == Decimal("2.000")

    assert banana.id not in consumption_map


@pytest.mark.asyncio
async def test_confirm_idempotency_deducts_once(
    db_session: AsyncSession,
) -> None:
    """Test 5: Confirm twice with same Idempotency-Key deducts once."""
    await _boost_stock(db_session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(db_session, "BANANA", "DRY", Decimal("50"))
    await _boost_stock(db_session, "WHEY", "DRY", Decimal("100"))

    milk = await _ingredient(db_session, "MILK")
    fridge = await _location(db_session, "FRIDGE")

    milk_before = await _balance_for(db_session, milk.id, fridge.id)
    qty_before = Decimal(milk_before.qty_on_hand)

    key = "idempotency-test-key-001"
    sale = await _create_and_confirm_shake(db_session, idempotency_key=key)

    await db_session.refresh(milk_before)
    qty_after_first = Decimal(milk_before.qty_on_hand)
    assert qty_after_first == qty_before - Decimal("200")

    svc = SalesService(db_session)
    sale_again = await svc.confirm(sale.id, key, user_id=(await _user(db_session)).id)

    await db_session.refresh(milk_before)
    qty_after_second = Decimal(milk_before.qty_on_hand)
    assert qty_after_second == qty_after_first

    assert sale_again.id == sale.id
    assert sale_again.status == "CONFIRMED"


@pytest.mark.asyncio
async def test_preparing_to_completed_no_second_deduct(
    db_session: AsyncSession,
) -> None:
    """Test 6: PREPARING -> COMPLETED does NOT deduct again."""
    await _boost_stock(db_session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(db_session, "BANANA", "DRY", Decimal("50"))
    await _boost_stock(db_session, "WHEY", "DRY", Decimal("100"))

    milk = await _ingredient(db_session, "MILK")
    fridge = await _location(db_session, "FRIDGE")

    sale = await _create_and_confirm_shake(db_session)
    milk_after_confirm = await _balance_for(db_session, milk.id, fridge.id)
    qty_after_confirm = Decimal(milk_after_confirm.qty_on_hand)

    svc = SalesService(db_session)
    await svc.set_status(sale.id, "PREPARING")
    await db_session.refresh(milk_after_confirm)
    assert Decimal(milk_after_confirm.qty_on_hand) == qty_after_confirm

    await svc.add_payment(sale.id, method="CASH", amount=sale.total)
    completed = await svc.set_status(sale.id, "COMPLETED")

    await db_session.refresh(milk_after_confirm)
    assert Decimal(milk_after_confirm.qty_on_hand) == qty_after_confirm
    assert completed.status == "COMPLETED"


@pytest.mark.asyncio
async def test_cancel_before_preparing_returns_stock(
    db_session: AsyncSession,
) -> None:
    """Test 7a: Cancel before PREPARING returns stock via SALE_REVERSAL."""
    await _boost_stock(db_session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(db_session, "BANANA", "DRY", Decimal("50"))
    await _boost_stock(db_session, "WHEY", "DRY", Decimal("100"))

    milk = await _ingredient(db_session, "MILK")
    fridge = await _location(db_session, "FRIDGE")
    milk_before = await _balance_for(db_session, milk.id, fridge.id)
    qty_before = Decimal(milk_before.qty_on_hand)

    sale = await _create_and_confirm_shake(db_session)
    await db_session.refresh(milk_before)
    assert Decimal(milk_before.qty_on_hand) == qty_before - Decimal("200")

    svc = SalesService(db_session)
    cancelled = await svc.cancel(sale.id, user_id=(await _user(db_session)).id)

    await db_session.refresh(milk_before)
    assert Decimal(milk_before.qty_on_hand) == qty_before
    assert cancelled.status == "CANCELLED"

    reversals = await db_session.execute(
        select(StockMovement).where(
            StockMovement.type == "SALE_REVERSAL",
            StockMovement.reference_id == sale.id,
        )
    )
    assert len(list(reversals.scalars().all())) > 0


@pytest.mark.asyncio
async def test_cancel_after_preparing_waste_no_return(
    db_session: AsyncSession,
) -> None:
    """Test 7b: Cancel after PREPARING with waste creates WASTE, no return."""
    await _boost_stock(db_session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(db_session, "BANANA", "DRY", Decimal("50"))
    await _boost_stock(db_session, "WHEY", "DRY", Decimal("100"))

    milk = await _ingredient(db_session, "MILK")
    fridge = await _location(db_session, "FRIDGE")

    sale = await _create_and_confirm_shake(db_session)
    milk_after_confirm = await _balance_for(db_session, milk.id, fridge.id)
    qty_after_confirm = Decimal(milk_after_confirm.qty_on_hand)

    svc = SalesService(db_session)
    await svc.set_status(sale.id, "PREPARING")
    cancelled = await svc.cancel(sale.id, user_id=(await _user(db_session)).id)

    await db_session.refresh(milk_after_confirm)
    assert Decimal(milk_after_confirm.qty_on_hand) == qty_after_confirm

    waste_movements = await db_session.execute(
        select(StockMovement).where(
            StockMovement.type == "WASTE",
            StockMovement.reference_id == sale.id,
        )
    )
    assert len(list(waste_movements.scalars().all())) > 0
    assert cancelled.status == "CANCELLED"


@pytest.mark.asyncio
async def test_cogs_snapshot_unchanged_after_wac_change(
    db_session: AsyncSession,
) -> None:
    """Test 9: COGS snapshot is immutable after WAC changes."""
    await _boost_stock(db_session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(db_session, "BANANA", "DRY", Decimal("50"))
    await _boost_stock(db_session, "WHEY", "DRY", Decimal("100"))

    sale = await _create_and_confirm_shake(db_session)
    original_cogs = Decimal(sale.cogs_total)
    assert original_cogs == Decimal("62.00")

    milk = await _ingredient(db_session, "MILK")
    milk.wac = Decimal("0.12")
    await db_session.flush()

    svc = SalesService(db_session)
    reloaded = await svc._load_sale(sale.id)
    assert Decimal(reloaded.cogs_total) == original_cogs

    stored_consumptions = await db_session.execute(
        select(SaleItemConsumption).where(
            SaleItemConsumption.sale_item_id == sale.items[0].id
        )
    )
    for c in stored_consumptions.scalars().all():
        if c.ingredient_id == milk.id:
            assert c.unit_cost == Decimal("0.060000")


@pytest.mark.asyncio
async def test_block_refuses_insufficient_stock(
    db_session: AsyncSession,
) -> None:
    """Test 14a: BLOCK policy raises INSUFFICIENT_STOCK."""
    await _set_policy(db_session, "BLOCK")

    banana = await _ingredient(db_session, "BANANA")
    dry = await _location(db_session, "DRY")
    bal = await _balance_for(db_session, banana.id, dry.id)
    current = Decimal(bal.qty_on_hand) if bal else Decimal("0")
    if current > 0:
        await InventoryService(db_session).apply_waste(
            ingredient_id=banana.id,
            location_id=dry.id,
            quantity_base=current,
            reason="Test setup - clear stock",
        )

    user = await _user(db_session)
    branch = await _branch(db_session)
    variant = await _variant_by_sku(db_session, "BANANA_PROTEIN_SHAKE")

    svc = SalesService(db_session)
    sale = await svc.create_sale(
        branch_id=branch.id,
        user_id=user.id,
        order_type="dine_in",
        items=[{"variant_id": variant.id, "qty": 1}],
    )

    with pytest.raises(AppError) as exc_info:
        await svc.confirm(sale.id, str(uuid4()), user_id=user.id)
    assert exc_info.value.code == "INSUFFICIENT_STOCK"
    assert "Banana" in exc_info.value.message


@pytest.mark.asyncio
async def test_warn_allows_and_flags(
    db_session: AsyncSession,
) -> None:
    """Test 14b: WARN policy allows sale and flags negative stock."""
    await _set_policy(db_session, "WARN")

    banana = await _ingredient(db_session, "BANANA")
    dry = await _location(db_session, "DRY")
    bal = await _balance_for(db_session, banana.id, dry.id)
    current = Decimal(bal.qty_on_hand) if bal else Decimal("0")
    if current > 0:
        await InventoryService(db_session).apply_waste(
            ingredient_id=banana.id,
            location_id=dry.id,
            quantity_base=current,
            reason="Test setup - clear stock",
        )

    await _boost_stock(db_session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(db_session, "WHEY", "DRY", Decimal("100"))

    user = await _user(db_session)
    branch = await _branch(db_session)
    variant = await _variant_by_sku(db_session, "BANANA_PROTEIN_SHAKE")

    svc = SalesService(db_session)
    sale = await svc.create_sale(
        branch_id=branch.id,
        user_id=user.id,
        order_type="dine_in",
        items=[{"variant_id": variant.id, "qty": 1}],
    )

    confirmed = await svc.confirm(sale.id, str(uuid4()), user_id=user.id)
    assert confirmed.flagged_negative_stock is True
    assert confirmed.status == "CONFIRMED"


@pytest.mark.asyncio
async def test_split_payment_must_sum_to_total(
    db_session: AsyncSession,
) -> None:
    """Test 18: Split payment must sum to total."""
    await _boost_stock(db_session, "MILK", "FRIDGE", Decimal("20000"))
    await _boost_stock(db_session, "BANANA", "DRY", Decimal("50"))
    await _boost_stock(db_session, "WHEY", "DRY", Decimal("100"))

    sale = await _create_and_confirm_shake(db_session)
    svc = SalesService(db_session)

    await svc.add_payment(sale.id, method="CASH", amount=Decimal("60"))
    await svc.add_payment(sale.id, method="CARD", amount=Decimal("40"))

    await svc.set_status(sale.id, "PREPARING")

    with pytest.raises(AppError) as exc_info:
        await svc.set_status(sale.id, "COMPLETED")
    assert exc_info.value.code == "PAYMENT_INCOMPLETE"

    await svc.add_payment(sale.id, method="WALLET", amount=Decimal("20"))

    sale_reloaded = await svc._load_sale(sale.id)
    total_paid = sum(Decimal(p.amount) for p in sale_reloaded.payments)
    assert total_paid == Decimal(sale_reloaded.total)

    completed = await svc.set_status(sale_reloaded.id, "COMPLETED")
    assert completed.status == "COMPLETED"


@pytest.mark.asyncio
async def test_concurrent_confirms_last_banana_block(engine) -> None:
    """Test 15: Two concurrent confirms for last banana under BLOCK."""
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with factory() as setup_session:
        user = await _user(setup_session)
        branch = await _branch(setup_session)
        banana = await _ingredient(setup_session, "BANANA")
        dry = await _location(setup_session, "DRY")
        variant = await _variant_by_sku(
            setup_session, "BANANA_PROTEIN_SHAKE"
        )

        bal = await _balance_for(setup_session, banana.id, dry.id)
        current = Decimal(bal.qty_on_hand) if bal else Decimal("0")
        if current > Decimal("1"):
            await InventoryService(setup_session).apply_waste(
                ingredient_id=banana.id,
                location_id=dry.id,
                quantity_base=current - Decimal("1"),
                reason="Test setup - reduce to 1",
            )
        elif current < Decimal("1"):
            await InventoryService(setup_session).apply_purchase_receipt(
                ingredient_id=banana.id,
                location_id=dry.id,
                received_qty=Decimal("1") - current,
                unit_cost=banana.wac,
            )

        await _boost_stock(
            setup_session, "MILK", "FRIDGE", Decimal("40000")
        )
        await _boost_stock(
            setup_session, "WHEY", "DRY", Decimal("200")
        )

        await _set_policy(setup_session, "BLOCK")

        svc = SalesService(setup_session)
        sale1 = await svc.create_sale(
            branch_id=branch.id,
            user_id=user.id,
            order_type="dine_in",
            items=[{"variant_id": variant.id, "qty": 1}],
        )
        sale2 = await svc.create_sale(
            branch_id=branch.id,
            user_id=user.id,
            order_type="dine_in",
            items=[{"variant_id": variant.id, "qty": 1}],
        )

        sale1_id = sale1.id
        sale2_id = sale2.id
        user_id = user.id

        await setup_session.commit()

    async def do_confirm(sale_id: UUID, key: str):
        async with factory() as s:
            result = await SalesService(s).confirm(
                sale_id, key, user_id=user_id
            )
            await s.commit()
            return result

    results = await asyncio.gather(
        do_confirm(sale1_id, "concurrent-key-1"),
        do_confirm(sale2_id, "concurrent-key-2"),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [
        r
        for r in results
        if isinstance(r, Exception) and isinstance(r, AppError)
    ]

    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].code == "INSUFFICIENT_STOCK"

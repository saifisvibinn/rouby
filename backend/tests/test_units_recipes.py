from decimal import Decimal

import pytest
import pytest_asyncio
from app.models.catalog import Ingredient, Product, ProductVariant, RecipeItem, RecipeVersion, Unit
from app.seed.runner import seed_all
from app.services.recipe_service import RecipeService
from app.services.unit_conversion import UnitConversionError, UnitConversionService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


@pytest_asyncio.fixture(autouse=True)
async def seeded_catalog(db_session: AsyncSession) -> None:
    await seed_all(db_session)


async def _unit(db_session: AsyncSession, code: str) -> Unit:
    result = await db_session.execute(select(Unit).where(Unit.code == code))
    return result.scalar_one()


async def _ingredient(db_session: AsyncSession, sku: str) -> Ingredient:
    result = await db_session.execute(select(Ingredient).where(Ingredient.sku == sku))
    return result.scalar_one()


async def _variant(db_session: AsyncSession, product_sku: str, variant_sku: str) -> ProductVariant:
    result = await db_session.execute(
        select(ProductVariant)
        .join(Product)
        .where(Product.sku == product_sku, ProductVariant.sku == variant_sku)
    )
    return result.scalar_one()


async def _recipe_versions(db_session: AsyncSession, variant_id) -> list[RecipeVersion]:
    result = await db_session.execute(
        select(RecipeVersion)
        .where(RecipeVersion.variant_id == variant_id)
        .options(selectinload(RecipeVersion.items).selectinload(RecipeItem.ingredient))
        .order_by(RecipeVersion.version_number)
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_convert_kg_to_g(db_session: AsyncSession) -> None:
    converted = await UnitConversionService(db_session).convert(Decimal("5"), "kg", "g")

    assert converted == Decimal("5000.000000")


@pytest.mark.asyncio
async def test_convert_g_to_ml_without_density_raises(db_session: AsyncSession) -> None:
    with pytest.raises(UnitConversionError) as exc:
        await UnitConversionService(db_session).convert(Decimal("1"), "g", "ml")

    assert exc.value.code == "INCOMPATIBLE_UNITS"


@pytest.mark.asyncio
async def test_latte_small_and_large_milk_quantities(db_session: AsyncSession) -> None:
    service = RecipeService(db_session)
    small = await _variant(db_session, "LATTE", "LATTE-S")
    large = await _variant(db_session, "LATTE", "LATTE-L")

    small_milk = await service.recipe_qty_in_base(small.id, "MILK")
    large_milk = await service.recipe_qty_in_base(large.id, "MILK")

    assert small_milk == Decimal("150")
    assert large_milk == Decimal("300")


@pytest.mark.asyncio
async def test_recipe_versioning_keeps_history_and_cost_uses_active(
    db_session: AsyncSession,
) -> None:
    service = RecipeService(db_session)
    latte_medium = await _variant(db_session, "LATTE", "LATTE-M")
    milk = await _ingredient(db_session, "MILK")
    ml = await _unit(db_session, "ml")
    first_versions = await _recipe_versions(db_session, latte_medium.id)

    assert len(first_versions) == 1
    assert first_versions[0].items[0].quantity == Decimal("200.000")

    new_version = await service.create_version(
        latte_medium.id,
        [
            {
                "ingredient_id": milk.id,
                "quantity": Decimal("250"),
                "unit_id": ml.id,
            }
        ],
    )
    await db_session.commit()

    versions = await _recipe_versions(db_session, latte_medium.id)
    old_version = versions[0]
    active_version = versions[1]
    theoretical_cost = await service.theoretical_cost(latte_medium.id)

    assert new_version.version_number == 2
    assert old_version.is_active is False
    assert old_version.items[0].quantity == Decimal("200.000")
    assert active_version.is_active is True
    assert active_version.items[0].quantity == Decimal("250.000")
    assert theoretical_cost == Decimal("15.00")

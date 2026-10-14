from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Location
from app.models.catalog import Ingredient
from app.models.inventory import StockMovement
from app.services.inventory_service import InventoryService

INITIAL_STOCK: dict[str, tuple[str, Decimal]] = {
    "MILK": ("FRIDGE", Decimal("3000")),
    "LACTOSE_FREE_MILK": ("FRIDGE", Decimal("1000")),
    "BANANA": ("DRY", Decimal("20")),
    "WHEY": ("DRY", Decimal("10")),
    "COFFEE_BEANS": ("DRY", Decimal("1000")),
    "STRAWBERRY": ("FRIDGE", Decimal("1000")),
    "GREEK_YOGURT": ("FRIDGE", Decimal("2000")),
    "GRANOLA": ("DRY", Decimal("1000")),
    "PEANUT_BUTTER": ("DRY", Decimal("1000")),
    "WATER_BOTTLE": ("DRY", Decimal("24")),
    "CHICKEN": ("FRIDGE", Decimal("3000")),
    "MOZZARELLA": ("FRIDGE", Decimal("1000")),
    "TORTILLA": ("DRY", Decimal("20")),
}


async def seed_inventory(session: AsyncSession) -> None:
    service = InventoryService(session)
    locations = await _locations_by_code(session)
    ingredients = await _ingredients_by_sku(session)

    for sku, (location_code, quantity) in INITIAL_STOCK.items():
        ingredient = ingredients[sku]
        location = locations[location_code]
        result = await session.execute(
            select(StockMovement).where(
                StockMovement.reference_type == "seed_inventory",
                StockMovement.reference_id == ingredient.id,
            )
        )
        if result.scalar_one_or_none() is not None:
            continue
        await service.apply_purchase_receipt(
            ingredient_id=ingredient.id,
            location_id=location.id,
            received_qty=quantity,
            unit_cost=ingredient.wac,
            reference_type="seed_inventory",
            reference_id=ingredient.id,
        )
    await session.flush()


async def _locations_by_code(session: AsyncSession) -> dict[str, Location]:
    result = await session.execute(select(Location))
    return {location.code: location for location in result.scalars().all()}


async def _ingredients_by_sku(session: AsyncSession) -> dict[str, Ingredient]:
    result = await session.execute(select(Ingredient))
    return {ingredient.sku: ingredient for ingredient in result.scalars().all()}

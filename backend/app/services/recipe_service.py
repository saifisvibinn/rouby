from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError, NotFoundError
from app.models.catalog import (
    Ingredient,
    ProductVariant,
    RecipeItem,
    RecipeVersion,
    Unit,
)
from app.services.unit_conversion import UnitConversionService


class RecipeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._units = UnitConversionService(session)

    async def get_active_version(self, variant_id: UUID) -> RecipeVersion | None:
        result = await self._session.execute(
            select(RecipeVersion)
            .where(
                RecipeVersion.variant_id == variant_id,
                RecipeVersion.is_active.is_(True),
            )
            .options(
                selectinload(RecipeVersion.items)
                .selectinload(RecipeItem.ingredient)
                .selectinload(Ingredient.storage_unit),
                selectinload(RecipeVersion.items).selectinload(RecipeItem.unit),
            )
            .order_by(RecipeVersion.version_number.desc())
        )
        return result.scalars().first()

    async def get_history(self, variant_id: UUID) -> list[RecipeVersion]:
        result = await self._session.execute(
            select(RecipeVersion)
            .where(RecipeVersion.variant_id == variant_id)
            .options(
                selectinload(RecipeVersion.items)
                .selectinload(RecipeItem.ingredient)
                .selectinload(Ingredient.storage_unit),
                selectinload(RecipeVersion.items).selectinload(RecipeItem.unit),
            )
            .order_by(RecipeVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def create_version(
        self,
        variant_id: UUID,
        items: list[dict],
        *,
        created_by_id: UUID | None = None,
    ) -> RecipeVersion:
        variant = await self._session.get(ProductVariant, variant_id)
        if variant is None:
            raise NotFoundError("Variant not found")

        result = await self._session.execute(
            select(RecipeVersion.version_number)
            .where(RecipeVersion.variant_id == variant_id)
            .order_by(RecipeVersion.version_number.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        next_num = (last or 0) + 1

        await self._session.execute(
            update(RecipeVersion)
            .where(
                RecipeVersion.variant_id == variant_id,
                RecipeVersion.is_active.is_(True),
            )
            .values(is_active=False)
        )

        version = RecipeVersion(
            variant_id=variant_id,
            version_number=next_num,
            is_active=True,
            created_by_id=created_by_id,
        )
        self._session.add(version)
        await self._session.flush()

        for item in items:
            qty = Decimal(str(item["quantity"]))
            if qty <= 0:
                raise AppError(
                    "INVALID_RECIPE",
                    "Recipe quantity must be positive",
                    status_code=422,
                )
            self._session.add(
                RecipeItem(
                    recipe_version_id=version.id,
                    ingredient_id=UUID(str(item["ingredient_id"])),
                    quantity=qty,
                    unit_id=UUID(str(item["unit_id"])),
                )
            )
        await self._session.flush()
        loaded = await self.get_active_version(variant_id)
        assert loaded is not None
        return loaded

    async def theoretical_cost(self, variant_id: UUID) -> Decimal:
        version = await self.get_active_version(variant_id)
        if version is None:
            return Decimal("0.00")
        total = Decimal("0")
        for item in version.items:
            unit = item.unit
            if unit is None:
                unit = await self._session.get(Unit, item.unit_id)
            assert unit is not None
            qty_base = await self._units.to_storage_base(item.quantity, unit, item.ingredient)
            total += qty_base * item.ingredient.wac
        return total.quantize(Decimal("0.01"))

    async def recipe_qty_in_base(
        self, variant_id: UUID, ingredient_sku: str
    ) -> Decimal:
        version = await self.get_active_version(variant_id)
        if version is None:
            return Decimal("0")
        for item in version.items:
            if item.ingredient.sku == ingredient_sku:
                unit = item.unit or await self._session.get(Unit, item.unit_id)
                assert unit is not None
                return await self._units.to_storage_base(
                    item.quantity, unit, item.ingredient
                )
        return Decimal("0")

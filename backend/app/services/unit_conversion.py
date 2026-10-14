from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.catalog import Ingredient, IngredientUnitConversion, Unit


class UnitConversionError(AppError):
    def __init__(self, message: str, *, code: str = "INVALID_UNIT_CONVERSION") -> None:
        super().__init__(code, message, status_code=422)


class UnitConversionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def convert(
        self,
        quantity: Decimal,
        from_unit_code: str,
        to_unit_code: str,
        *,
        ingredient_id: UUID | None = None,
    ) -> Decimal:
        if quantity < 0:
            raise UnitConversionError("Quantity cannot be negative")

        from_unit = await self._get_unit_by_code(from_unit_code)
        to_unit = await self._get_unit_by_code(to_unit_code)

        if from_unit.id == to_unit.id:
            return quantity

        ingredient: Ingredient | None = None
        if ingredient_id is not None:
            ingredient = await self._get_ingredient(ingredient_id)

        if from_unit.dimension == to_unit.dimension:
            return (quantity * from_unit.factor_to_base) / to_unit.factor_to_base

        if ingredient is not None:
            pack = await self._pack(ingredient.id, from_unit.id, to_unit.id)
            if pack is not None:
                return quantity * pack

            if ingredient.density_g_per_ml is not None:
                density = ingredient.density_g_per_ml
                if from_unit.dimension == "mass" and to_unit.dimension == "volume":
                    grams = quantity * from_unit.factor_to_base
                    ml = grams / density
                    return ml / to_unit.factor_to_base
                if from_unit.dimension == "volume" and to_unit.dimension == "mass":
                    ml = quantity * from_unit.factor_to_base
                    grams = ml * density
                    return grams / to_unit.factor_to_base

        raise UnitConversionError(
            f"Cannot convert {from_unit.code} to {to_unit.code} across dimensions without density",
            code="INCOMPATIBLE_UNITS",
        )

    async def to_storage_base(
        self,
        quantity: Decimal,
        from_unit: Unit,
        ingredient: Ingredient,
    ) -> Decimal:
        """Convert recipe/purchase qty into ingredient storage unit base amount."""
        storage = ingredient.storage_unit
        if storage is None:
            result = await self._session.execute(
                select(Unit).where(Unit.id == ingredient.storage_unit_id)
            )
            storage = result.scalar_one()
        return await self.convert(
            quantity,
            from_unit.code,
            storage.code,
            ingredient_id=ingredient.id,
        )

    async def _pack(
        self, ingredient_id: UUID, from_unit_id: UUID, to_unit_id: UUID
    ) -> Decimal | None:
        result = await self._session.execute(
            select(IngredientUnitConversion).where(
                IngredientUnitConversion.ingredient_id == ingredient_id,
                IngredientUnitConversion.from_unit_id == from_unit_id,
                IngredientUnitConversion.to_unit_id == to_unit_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            return row.factor
        result = await self._session.execute(
            select(IngredientUnitConversion).where(
                IngredientUnitConversion.ingredient_id == ingredient_id,
                IngredientUnitConversion.from_unit_id == to_unit_id,
                IngredientUnitConversion.to_unit_id == from_unit_id,
            )
        )
        rev = result.scalar_one_or_none()
        if rev:
            return Decimal("1") / rev.factor
        return None

    async def _get_unit_by_code(self, code: str) -> Unit:
        result = await self._session.execute(select(Unit).where(Unit.code == code))
        unit = result.scalar_one_or_none()
        if unit is None:
            raise UnitConversionError(f"Unit {code} not found", code="UNIT_NOT_FOUND")
        return unit

    async def _get_ingredient(self, ingredient_id: UUID) -> Ingredient:
        result = await self._session.execute(
            select(Ingredient)
            .where(Ingredient.id == ingredient_id)
            .options(selectinload(Ingredient.storage_unit))
        )
        ing = result.scalar_one_or_none()
        if ing is None:
            raise UnitConversionError("Ingredient not found", code="INGREDIENT_NOT_FOUND")
        return ing

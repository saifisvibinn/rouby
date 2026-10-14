from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models.catalog import (
    Ingredient,
    Modifier,
    ModifierEffect,
    RecipeItem,
    RecipeVersion,
    Unit,
)
from app.services.recipe_service import RecipeService
from app.services.unit_conversion import UnitConversionService


@dataclass
class ResolvedLine:
    ingredient_id: UUID
    qty_base: Decimal


@dataclass
class ResolvedRecipe:
    recipe_version_id: UUID | None
    lines: list[ResolvedLine] = field(default_factory=list)
    price_delta: Decimal = Decimal("0")


class ModifierResolutionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._units = UnitConversionService(session)
        self._recipes = RecipeService(session)

    async def resolve(
        self,
        variant_id: UUID,
        modifier_ids: list[UUID] | None = None,
    ) -> ResolvedRecipe:
        recipe = await self._recipes.get_active_version(variant_id)
        if recipe is None:
            return ResolvedRecipe(recipe_version_id=None)

        lines: dict[UUID, Decimal] = {}
        for item in recipe.items:
            ingredient = item.ingredient
            unit = item.unit or await self._session.get(Unit, item.unit_id)
            if ingredient is None:
                result = await self._session.execute(
                    select(Ingredient).where(Ingredient.id == item.ingredient_id)
                )
                ingredient = result.scalar_one()
            qty_base = await self._units.to_storage_base(
                item.quantity, unit, ingredient
            )
            lines[item.ingredient_id] = qty_base

        price_delta = Decimal("0")
        for modifier_id in modifier_ids or []:
            modifier = await self._load_modifier(modifier_id)
            price_delta += modifier.price_delta
            for effect in modifier.effects:
                self._apply_effect(effect, lines)
                if effect.effect_type == "ADD" and effect.ingredient_id is not None:
                    add_qty = await self._resolve_add_qty(effect)
                    lines[effect.ingredient_id] = lines.get(
                        effect.ingredient_id, Decimal("0")
                    ) + add_qty
                elif effect.effect_type == "REPLACE":
                    await self._apply_replace(effect, lines)

        resolved_lines = [
            ResolvedLine(ingredient_id=ing_id, qty_base=qty)
            for ing_id, qty in lines.items()
            if qty > 0
        ]
        return ResolvedRecipe(
            recipe_version_id=recipe.id,
            lines=resolved_lines,
            price_delta=price_delta,
        )

    def _apply_effect(
        self, effect: ModifierEffect, lines: dict[UUID, Decimal]
    ) -> None:
        if effect.effect_type == "REMOVE" and effect.ingredient_id is not None:
            lines.pop(effect.ingredient_id, None)
        elif (
            effect.effect_type == "MULTIPLY"
            and effect.ingredient_id is not None
            and effect.multiply_factor is not None
        ):
            if effect.ingredient_id in lines:
                lines[effect.ingredient_id] = (
                    lines[effect.ingredient_id] * effect.multiply_factor
                )

    async def _resolve_add_qty(self, effect: ModifierEffect) -> Decimal:
        if effect.quantity is None or effect.unit_id is None:
            return Decimal("0")
        ingredient = await self._get_ingredient(effect.ingredient_id)
        unit = await self._session.get(Unit, effect.unit_id)
        if unit is None:
            return Decimal("0")
        return await self._units.to_storage_base(
            effect.quantity, unit, ingredient
        )

    async def _apply_replace(
        self, effect: ModifierEffect, lines: dict[UUID, Decimal]
    ) -> None:
        if (
            effect.ingredient_id is None
            or effect.replace_with_ingredient_id is None
        ):
            return
        if effect.ingredient_id not in lines:
            return
        original_qty = lines.pop(effect.ingredient_id)
        lines[effect.replace_with_ingredient_id] = (
            lines.get(effect.replace_with_ingredient_id, Decimal("0"))
            + original_qty
        )

    async def _load_modifier(self, modifier_id: UUID) -> Modifier:
        result = await self._session.execute(
            select(Modifier)
            .where(Modifier.id == modifier_id)
            .options(selectinload(Modifier.effects))
        )
        modifier = result.scalar_one_or_none()
        if modifier is None:
            raise NotFoundError("Modifier not found")
        return modifier

    async def _get_ingredient(self, ingredient_id: UUID) -> Ingredient:
        result = await self._session.execute(
            select(Ingredient).where(Ingredient.id == ingredient_id)
        )
        ingredient = result.scalar_one_or_none()
        if ingredient is None:
            raise NotFoundError("Ingredient not found")
        return ingredient

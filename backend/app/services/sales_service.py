from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError, NotFoundError
from app.models.catalog import Ingredient, Modifier, ProductVariant
from app.models.inventory import InventoryBalance
from app.models.sales import (
    IdempotencyKey,
    Payment,
    Sale,
    SaleItem,
    SaleItemConsumption,
    SaleItemModifier,
)
from app.models.settings import Setting
from app.services.inventory_service import InventoryService
from app.services.modifier_resolution import ModifierResolutionService, ResolvedRecipe

QTY = Decimal("0.001")
COST = Decimal("0.000001")
MONEY = Decimal("0.01")

VALID_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"PREPARING", "CANCELLED"},
    "PREPARING": {"COMPLETED", "CANCELLED"},
}


class SalesService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inv = InventoryService(session)
        self._resolver = ModifierResolutionService(session)

    async def create_sale(
        self,
        *,
        branch_id: UUID,
        user_id: UUID,
        order_type: str = "dine_in",
        items: list[dict],
        discount: Decimal = Decimal("0"),
    ) -> Sale:
        tax_rate = await self._get_tax_rate()

        sale = Sale(
            branch_id=branch_id,
            user_id=user_id,
            order_type=order_type,
            discount=Decimal(str(discount)).quantize(MONEY),
        )
        self._session.add(sale)
        await self._session.flush()

        subtotal = Decimal("0")
        for item_data in items:
            variant = await self._get_variant(item_data["variant_id"])
            modifier_ids: list[UUID] = [
                UUID(str(mid)) for mid in item_data.get("modifier_ids", [])
            ]
            modifiers = [
                await self._get_modifier(mid) for mid in modifier_ids
            ]
            price_delta = sum(
                (Decimal(m.price_delta) for m in modifiers), Decimal("0")
            )
            unit_price = (Decimal(variant.price) + price_delta).quantize(MONEY)
            qty = int(item_data["qty"])
            line_total = (unit_price * qty).quantize(MONEY)

            sale_item = SaleItem(
                sale_id=sale.id,
                variant_id=variant.id,
                qty=qty,
                unit_price=unit_price,
                line_total=line_total,
                notes=item_data.get("notes"),
            )
            self._session.add(sale_item)
            await self._session.flush()

            for mod in modifiers:
                self._session.add(
                    SaleItemModifier(
                        sale_item_id=sale_item.id,
                        modifier_id=mod.id,
                        price_delta=Decimal(mod.price_delta).quantize(MONEY),
                    )
                )
            subtotal += line_total

        sale.subtotal = subtotal
        tax = (subtotal * tax_rate / 100).quantize(MONEY)
        sale.tax = tax
        sale.total = (subtotal - sale.discount + tax).quantize(MONEY)
        await self._session.flush()

        return await self._load_sale(sale.id)

    async def update_sale(
        self,
        sale_id: UUID,
        *,
        items: list[dict] | None = None,
        discount: Decimal | None = None,
        order_type: str | None = None,
    ) -> Sale:
        sale = await self._load_sale(sale_id)
        if sale.status != "DRAFT":
            raise AppError(
                "INVALID_SALE_STATUS",
                "Only draft sales can be updated",
            )
        if order_type is not None:
            sale.order_type = order_type
        if discount is not None:
            sale.discount = Decimal(str(discount)).quantize(MONEY)

        if items is not None:
            for old_item in list(sale.items):
                await self._session.delete(old_item)
            await self._session.flush()

            tax_rate = await self._get_tax_rate()
            subtotal = Decimal("0")
            for item_data in items:
                variant = await self._get_variant(item_data["variant_id"])
                modifier_ids: list[UUID] = [
                    UUID(str(mid)) for mid in item_data.get("modifier_ids", [])
                ]
                modifiers = [
                    await self._get_modifier(mid) for mid in modifier_ids
                ]
                price_delta = sum(
                    (Decimal(m.price_delta) for m in modifiers), Decimal("0")
                )
                unit_price = (
                    Decimal(variant.price) + price_delta
                ).quantize(MONEY)
                qty = int(item_data["qty"])
                line_total = (unit_price * qty).quantize(MONEY)

                sale_item = SaleItem(
                    sale_id=sale.id,
                    variant_id=variant.id,
                    qty=qty,
                    unit_price=unit_price,
                    line_total=line_total,
                    notes=item_data.get("notes"),
                )
                self._session.add(sale_item)
                await self._session.flush()

                for mod in modifiers:
                    self._session.add(
                        SaleItemModifier(
                            sale_item_id=sale_item.id,
                            modifier_id=mod.id,
                            price_delta=Decimal(mod.price_delta).quantize(MONEY),
                        )
                    )
                subtotal += line_total

            sale.subtotal = subtotal
            tax = (subtotal * tax_rate / 100).quantize(MONEY)
            sale.tax = tax
            sale.total = (subtotal - sale.discount + tax).quantize(MONEY)

        await self._session.flush()
        return await self._load_sale(sale.id)

    async def confirm(
        self,
        sale_id: UUID,
        idempotency_key: str,
        *,
        user_id: UUID | None = None,
    ) -> Sale:
        existing = await self._check_idempotency(idempotency_key)
        if existing is not None:
            return await self._load_sale(
                UUID(existing.response_body["sale_id"])
            )

        sale = await self._load_sale(sale_id)
        if sale.status == "CONFIRMED":
            return sale
        if sale.status != "DRAFT":
            raise AppError(
                "INVALID_SALE_STATUS",
                "Only draft sales can be confirmed",
                status_code=status.HTTP_409_CONFLICT,
            )

        policy = await self._get_setting("negative_stock_policy")

        items_recipes: list[tuple[SaleItem, ResolvedRecipe]] = []
        for item in sale.items:
            modifier_ids = [m.modifier_id for m in item.modifiers]
            resolved = await self._resolver.resolve(
                item.variant_id, modifier_ids
            )
            items_recipes.append((item, resolved))

        ingredient_needs: dict[UUID, Decimal] = {}
        for item, recipe in items_recipes:
            for line in recipe.lines:
                total = (line.qty_base * item.qty).quantize(QTY)
                ingredient_needs[line.ingredient_id] = (
                    ingredient_needs.get(line.ingredient_id, Decimal("0"))
                    + total
                )

        sorted_ids = sorted(ingredient_needs.keys(), key=str)

        balances: dict[UUID, InventoryBalance | None] = {}
        for ing_id in sorted_ids:
            result = await self._session.execute(
                select(InventoryBalance)
                .where(
                    InventoryBalance.ingredient_id == ing_id,
                    InventoryBalance.branch_id == sale.branch_id,
                )
                .with_for_update()
            )
            balances[ing_id] = result.scalar_one_or_none()

        flagged = False
        for ing_id in sorted_ids:
            needed = ingredient_needs[ing_id]
            balance = balances[ing_id]
            available = (
                Decimal(balance.qty_on_hand)
                if balance is not None
                else Decimal("0")
            )
            if available < needed:
                if policy == "BLOCK":
                    ingredient = await self._session.get(Ingredient, ing_id)
                    name = ingredient.name_en if ingredient else str(ing_id)
                    raise AppError(
                        "INSUFFICIENT_STOCK",
                        f"Insufficient stock for {name}",
                        status_code=status.HTTP_409_CONFLICT,
                    )
                flagged = True

        ingredient_wacs: dict[UUID, Decimal] = {}
        for ing_id in sorted_ids:
            ingredient = await self._session.get(Ingredient, ing_id)
            ingredient_wacs[ing_id] = Decimal(ingredient.wac)

        for ing_id in sorted_ids:
            needed = ingredient_needs[ing_id]
            balance = balances[ing_id]
            if balance is None:
                balance = await self._inv._lock_balance(
                    ing_id,
                    (await self._default_location(sale.branch_id)).id,
                    sale.branch_id,
                )
            await self._inv._post_movement_on_balance(
                balance=balance,
                type="SALE",
                quantity_base=needed,
                unit_cost=ingredient_wacs[ing_id],
                reference_type="sale",
                reference_id=sale.id,
                user_id=user_id,
                reason="Sale confirmed",
                allow_negative_balance=(policy == "WARN"),
            )
            try:
                await self._inv.allocate_fefo(
                    ing_id,
                    balance.location_id,
                    needed,
                    allow_partial=True,
                )
            except AppError:
                pass

        cogs_total = Decimal("0")
        for item, recipe in items_recipes:
            item.recipe_version_id = recipe.recipe_version_id
            item_cogs = Decimal("0")
            for line in recipe.lines:
                total_qty = (line.qty_base * item.qty).quantize(QTY)
                wac = ingredient_wacs[line.ingredient_id]
                line_cogs = (total_qty * wac).quantize(MONEY)
                self._session.add(
                    SaleItemConsumption(
                        sale_item_id=item.id,
                        ingredient_id=line.ingredient_id,
                        qty_base=total_qty,
                        unit_cost=wac,
                        line_cogs=line_cogs,
                    )
                )
                item_cogs += line_cogs
            item.cogs = item_cogs
            cogs_total += item_cogs

        sale.cogs_total = cogs_total
        sale.flagged_negative_stock = flagged
        sale.status = "CONFIRMED"
        await self._session.flush()

        await self._store_idempotency(
            idempotency_key,
            method="POST",
            path=f"/sales/{sale.id}/confirm",
            response_code=200,
            response_body={"sale_id": str(sale.id)},
        )
        await self._session.flush()

        return await self._load_sale(sale.id)

    async def set_status(
        self,
        sale_id: UUID,
        target_status: str,
    ) -> Sale:
        sale = await self._load_sale(sale_id)
        allowed = VALID_TRANSITIONS.get(sale.status, set())
        if target_status not in allowed:
            raise AppError(
                "INVALID_STATUS_TRANSITION",
                f"Cannot transition from {sale.status} to {target_status}",
                status_code=status.HTTP_409_CONFLICT,
            )

        if target_status == "CONFIRMED":
            raise AppError(
                "USE_CONFIRM_ENDPOINT",
                "Use the /confirm endpoint to confirm a sale",
            )

        if target_status == "COMPLETED":
            total_paid = sum(
                Decimal(p.amount) for p in sale.payments
            )
            if total_paid != Decimal(sale.total):
                raise AppError(
                    "PAYMENT_INCOMPLETE",
                    "Payments must sum to total before completing",
                    status_code=status.HTTP_409_CONFLICT,
                    details={
                        "total": str(sale.total),
                        "paid": str(total_paid),
                    },
                )

        sale.status = target_status
        await self._session.flush()
        return await self._load_sale(sale.id)

    async def cancel(
        self,
        sale_id: UUID,
        *,
        user_id: UUID | None = None,
        line_dispositions: list[dict] | None = None,
    ) -> Sale:
        sale = await self._load_sale(sale_id)

        if sale.status == "COMPLETED":
            raise AppError(
                "CANNOT_CANCEL_COMPLETED",
                "Completed sales cannot be cancelled",
                status_code=status.HTTP_409_CONFLICT,
            )
        if sale.status == "CANCELLED":
            return sale

        if sale.status == "DRAFT":
            sale.status = "CANCELLED"
            await self._session.flush()
            return await self._load_sale(sale.id)

        if sale.status == "CONFIRMED":
            await self._reverse_all_consumptions(sale, user_id)
            sale.status = "CANCELLED"
            await self._session.flush()
            return await self._load_sale(sale.id)

        if sale.status == "PREPARING":
            await self._handle_preparing_cancel(
                sale, user_id, line_dispositions or []
            )
            sale.status = "CANCELLED"
            await self._session.flush()
            return await self._load_sale(sale.id)

        raise AppError("INVALID_SALE_STATUS", "Cannot cancel from this status")

    async def add_payment(
        self,
        sale_id: UUID,
        *,
        method: str,
        amount: Decimal,
    ) -> Payment:
        sale = await self._load_sale(sale_id)
        if sale.status in ("COMPLETED", "CANCELLED"):
            raise AppError(
                "INVALID_SALE_STATUS",
                "Cannot add payment to completed or cancelled sale",
            )

        payment = Payment(
            sale_id=sale.id,
            method=method,
            amount=Decimal(str(amount)).quantize(MONEY),
        )
        self._session.add(payment)
        await self._session.flush()
        return payment

    async def get_menu(self, branch_id: UUID) -> list[dict]:
        from app.models.catalog import (
            Category,
            ModifierGroup,
            Product,
            ProductModifierGroup,
        )

        cats_result = await self._session.execute(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order)
        )
        categories = list(cats_result.scalars().all())

        prods_result = await self._session.execute(
            select(Product)
            .where(Product.is_active.is_(True))
            .options(selectinload(Product.variants))
            .order_by(Product.sort_order)
        )
        products = list(prods_result.scalars().all())

        pmg_result = await self._session.execute(select(ProductModifierGroup))
        pmgs = list(pmg_result.scalars().all())
        prod_mg_map: dict[UUID, list[UUID]] = {}
        for pmg in pmgs:
            prod_mg_map.setdefault(pmg.product_id, []).append(
                pmg.modifier_group_id
            )

        mg_ids = {mg_id for ids in prod_mg_map.values() for mg_id in ids}
        mod_groups: dict[UUID, dict] = {}
        if mg_ids:
            from app.models.catalog import Modifier as ModifierModel

            mg_result = await self._session.execute(
                select(ModifierGroup).where(
                    ModifierGroup.id.in_(mg_ids),
                    ModifierGroup.is_active.is_(True),
                )
            )
            for mg in mg_result.scalars().all():
                mod_result = await self._session.execute(
                    select(ModifierModel).where(
                        ModifierModel.modifier_group_id == mg.id,
                        ModifierModel.is_active.is_(True),
                    )
                )
                mods = list(mod_result.scalars().all())
                mod_groups[mg.id] = {
                    "id": str(mg.id),
                    "code": mg.code,
                    "name_en": mg.name_en,
                    "name_ar": mg.name_ar,
                    "min_select": mg.min_select,
                    "max_select": mg.max_select,
                    "modifiers": [
                        {
                            "id": str(m.id),
                            "code": m.code,
                            "name_en": m.name_en,
                            "name_ar": m.name_ar,
                            "price_delta": str(m.price_delta),
                        }
                        for m in mods
                    ],
                }

        bal_result = await self._session.execute(
            select(InventoryBalance).where(
                InventoryBalance.branch_id == branch_id
            )
        )
        balance_map: dict[UUID, Decimal] = {
            b.ingredient_id: Decimal(b.qty_on_hand)
            for b in bal_result.scalars().all()
        }

        products_by_cat: dict[UUID, list[Product]] = {}
        for p in products:
            products_by_cat.setdefault(p.category_id, []).append(p)

        menu = []
        for cat in categories:
            cat_products = products_by_cat.get(cat.id, [])
            cat_data = {
                "id": str(cat.id),
                "code": cat.code,
                "name_en": cat.name_en,
                "name_ar": cat.name_ar,
                "products": [],
            }
            for prod in cat_products:
                variants_out = []
                for v in prod.variants:
                    if not v.is_active:
                        continue
                    available = await self._check_variant_availability(
                        v.id, balance_map
                    )
                    variants_out.append(
                        {
                            "id": str(v.id),
                            "sku": v.sku,
                            "name_en": v.name_en,
                            "name_ar": v.name_ar,
                            "price": str(v.price),
                            "available": available,
                        }
                    )

                mg_list = [
                    mod_groups[mg_id]
                    for mg_id in prod_mg_map.get(prod.id, [])
                    if mg_id in mod_groups
                ]
                cat_data["products"].append(
                    {
                        "id": str(prod.id),
                        "sku": prod.sku,
                        "name_en": prod.name_en,
                        "name_ar": prod.name_ar,
                        "image_url": prod.image_url,
                        "modifier_groups": mg_list,
                        "variants": variants_out,
                    }
                )
            menu.append(cat_data)
        return menu

    async def _check_variant_availability(
        self,
        variant_id: UUID,
        balance_map: dict[UUID, Decimal],
    ) -> bool:
        try:
            resolved = await self._resolver.resolve(variant_id)
        except Exception:
            return False
        for line in resolved.lines:
            available = balance_map.get(line.ingredient_id, Decimal("0"))
            if available < line.qty_base:
                return False
        return True

    async def _reverse_all_consumptions(
        self,
        sale: Sale,
        user_id: UUID | None,
    ) -> None:
        for item in sale.items:
            for consumption in item.consumptions:
                balance = await self._find_balance(
                    consumption.ingredient_id, sale.branch_id
                )
                if balance is not None:
                    await self._inv._post_movement_on_balance(
                        balance=balance,
                        type="SALE_REVERSAL",
                        quantity_base=consumption.qty_base,
                        unit_cost=consumption.unit_cost,
                        reference_type="sale_cancel",
                        reference_id=sale.id,
                        user_id=user_id,
                        reason="Sale cancelled before preparing",
                    )

    async def _handle_preparing_cancel(
        self,
        sale: Sale,
        user_id: UUID | None,
        line_dispositions: list[dict],
    ) -> None:
        disposition_map: dict[UUID, str] = {
            UUID(str(d["sale_item_id"])): d.get("action", "waste")
            for d in line_dispositions
        }

        for item in sale.items:
            action = disposition_map.get(item.id, "waste")
            for consumption in item.consumptions:
                balance = await self._find_balance(
                    consumption.ingredient_id, sale.branch_id
                )
                if balance is None:
                    continue

                if action == "return":
                    await self._inv._post_movement_on_balance(
                        balance=balance,
                        type="SALE_REVERSAL",
                        quantity_base=consumption.qty_base,
                        unit_cost=consumption.unit_cost,
                        reference_type="sale_cancel",
                        reference_id=sale.id,
                        user_id=user_id,
                        reason="Sale cancelled after preparing - returned",
                    )
                else:
                    await self._inv._post_movement_on_balance(
                        balance=balance,
                        type="SALE_REVERSAL",
                        quantity_base=consumption.qty_base,
                        unit_cost=consumption.unit_cost,
                        reference_type="sale_cancel",
                        reference_id=sale.id,
                        user_id=user_id,
                        reason="Sale cancelled after preparing - reversal",
                    )
                    await self._inv._post_movement_on_balance(
                        balance=balance,
                        type="WASTE",
                        quantity_base=consumption.qty_base,
                        unit_cost=consumption.unit_cost,
                        reference_type="sale_waste",
                        reference_id=sale.id,
                        user_id=user_id,
                        reason="Sale cancelled after preparing - waste",
                        allow_negative_balance=True,
                    )

    async def _find_balance(
        self,
        ingredient_id: UUID,
        branch_id: UUID,
    ) -> InventoryBalance | None:
        result = await self._session.execute(
            select(InventoryBalance)
            .where(
                InventoryBalance.ingredient_id == ingredient_id,
                InventoryBalance.branch_id == branch_id,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def _default_location(self, branch_id: UUID):
        from app.models.branch import Location

        result = await self._session.execute(
            select(Location)
            .where(Location.branch_id == branch_id)
            .order_by(Location.created_at.asc())
            .limit(1)
        )
        loc = result.scalar_one_or_none()
        if loc is None:
            raise NotFoundError("No location found for branch")
        return loc

    async def _load_sale(self, sale_id: UUID) -> Sale:
        result = await self._session.execute(
            select(Sale)
            .where(Sale.id == sale_id)
            .options(
                selectinload(Sale.items).options(
                    selectinload(SaleItem.modifiers),
                    selectinload(SaleItem.consumptions),
                ),
                selectinload(Sale.payments),
            )
            .execution_options(populate_existing=True)
        )
        sale = result.scalar_one_or_none()
        if sale is None:
            raise NotFoundError("Sale not found")
        return sale

    async def _get_variant(self, variant_id: UUID) -> ProductVariant:
        variant = await self._session.get(ProductVariant, variant_id)
        if variant is None:
            raise NotFoundError("Product variant not found")
        return variant

    async def _get_modifier(self, modifier_id: UUID) -> Modifier:
        modifier = await self._session.get(Modifier, modifier_id)
        if modifier is None:
            raise NotFoundError("Modifier not found")
        return modifier

    async def _check_idempotency(
        self, key: str
    ) -> IdempotencyKey | None:
        result = await self._session.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == key)
        )
        return result.scalar_one_or_none()

    async def _store_idempotency(
        self,
        key: str,
        *,
        method: str,
        path: str,
        response_code: int,
        response_body: dict,
    ) -> IdempotencyKey:
        idem = IdempotencyKey(
            key=key,
            method=method,
            path=path,
            response_code=response_code,
            response_body=response_body,
        )
        self._session.add(idem)
        await self._session.flush()
        return idem

    async def _get_setting(self, key: str) -> str:
        result = await self._session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting is None:
            return ""
        return setting.value

    async def _get_tax_rate(self) -> Decimal:
        raw = await self._get_setting("tax_rate")
        try:
            return Decimal(raw)
        except Exception:
            return Decimal("0")

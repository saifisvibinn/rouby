from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import StringIO
from typing import Any

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Category, Ingredient, Product, ProductVariant
from app.models.inventory import InventoryBalance, StockMovement
from app.models.sales import Payment, Sale, SaleItem, SaleItemConsumption

MONEY = Decimal("0.01")
QTY = Decimal("0.001")
REPORT_SALE_STATUSES = ("CONFIRMED", "PREPARING", "COMPLETED")


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sales_report(
        self,
        *,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
    ) -> dict[str, Any]:
        order_count = await self._count_orders(from_at=from_at, to_at=to_at)
        total_sales = await self._sum_sale_lines(from_at=from_at, to_at=to_at)
        avg_ticket = self._money(total_sales / order_count) if order_count else Decimal("0.00")

        return {
            "from": from_at.isoformat() if from_at else None,
            "to": to_at.isoformat() if to_at else None,
            "totals": {
                "sales_total": str(self._money(total_sales)),
                "order_count": order_count,
                "avg_ticket": str(avg_ticket),
            },
            "by_category": await self._sales_by_category(from_at=from_at, to_at=to_at),
            "by_product": await self._sales_by_product(from_at=from_at, to_at=to_at),
            "by_payment": await self._sales_by_payment(from_at=from_at, to_at=to_at),
        }

    async def inventory_report(self) -> dict[str, Any]:
        valuation_rows = await self._session.execute(
            select(
                Ingredient.id,
                Ingredient.sku,
                Ingredient.name_en,
                Ingredient.min_stock,
                Ingredient.wac,
                func.coalesce(func.sum(InventoryBalance.qty_on_hand), 0),
            )
            .join(InventoryBalance, InventoryBalance.ingredient_id == Ingredient.id)
            .group_by(Ingredient.id, Ingredient.sku, Ingredient.name_en, Ingredient.min_stock, Ingredient.wac)
            .order_by(Ingredient.name_en)
        )

        items: list[dict[str, Any]] = []
        total_value = Decimal("0")
        for ingredient_id, sku, name, min_stock, wac, qty in valuation_rows.all():
            qty_on_hand = self._qty(qty)
            unit_cost = Decimal(wac)
            value = self._money(qty_on_hand * unit_cost)
            total_value += value
            items.append(
                {
                    "ingredient_id": str(ingredient_id),
                    "sku": sku,
                    "name": name,
                    "qty_on_hand": str(qty_on_hand),
                    "min_stock": str(self._qty(min_stock)),
                    "unit_cost": str(unit_cost),
                    "value": str(value),
                }
            )

        movement_rows = await self._session.execute(
            select(
                StockMovement.type,
                func.count(StockMovement.id),
                func.coalesce(func.sum(StockMovement.quantity_base), 0),
                func.coalesce(
                    func.sum(func.abs(StockMovement.quantity_base) * StockMovement.unit_cost),
                    0,
                ),
            )
            .group_by(StockMovement.type)
            .order_by(StockMovement.type)
        )

        return {
            "valuation": {
                "total_value": str(self._money(total_value)),
                "items": items,
            },
            "movement_summary": [
                {
                    "type": movement_type,
                    "movement_count": int(count),
                    "quantity_base": str(self._qty(quantity)),
                    "value": str(self._money(value)),
                }
                for movement_type, count, quantity, value in movement_rows.all()
            ],
        }

    async def profit_report(
        self,
        *,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
    ) -> dict[str, Any]:
        revenue = await self._sum_sale_lines(from_at=from_at, to_at=to_at)
        cogs = await self._sum_cogs(from_at=from_at, to_at=to_at)
        gross_profit = self._money(revenue - cogs)
        margin = self._margin(gross_profit, revenue)
        by_product = await self._profit_by_product(from_at=from_at, to_at=to_at)

        return {
            "from": from_at.isoformat() if from_at else None,
            "to": to_at.isoformat() if to_at else None,
            "totals": {
                "revenue": str(self._money(revenue)),
                "cogs": str(self._money(cogs)),
                "gross_profit": str(gross_profit),
                "margin_percent": str(margin),
            },
            "by_product": by_product,
            "by_category": await self._profit_by_category(from_at=from_at, to_at=to_at),
            "high_sales_low_margin": self._high_sales_low_margin(by_product),
        }

    async def usage_variance_report(self) -> dict[str, Any]:
        theoretical_rows = await self._session.execute(
            select(
                SaleItemConsumption.ingredient_id,
                func.coalesce(func.sum(SaleItemConsumption.qty_base), 0),
            )
            .join(SaleItem, SaleItem.id == SaleItemConsumption.sale_item_id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.status.in_(REPORT_SALE_STATUSES))
            .group_by(SaleItemConsumption.ingredient_id)
        )
        actual_rows = await self._session.execute(
            select(
                StockMovement.ingredient_id,
                func.coalesce(func.abs(func.sum(StockMovement.quantity_base)), 0),
            )
            .where(StockMovement.type == "SALE")
            .group_by(StockMovement.ingredient_id)
        )
        ingredient_rows = await self._session.execute(select(Ingredient))
        ingredients = {ingredient.id: ingredient for ingredient in ingredient_rows.scalars().all()}

        theoretical = {
            ingredient_id: self._qty(qty) for ingredient_id, qty in theoretical_rows.all()
        }
        actual = {ingredient_id: self._qty(qty) for ingredient_id, qty in actual_rows.all()}
        ingredient_ids = sorted(theoretical.keys() | actual.keys(), key=str)

        return {
            "items": [
                {
                    "ingredient_id": str(ingredient_id),
                    "sku": ingredients[ingredient_id].sku if ingredient_id in ingredients else None,
                    "name": ingredients[ingredient_id].name_en if ingredient_id in ingredients else None,
                    "theoretical_qty": str(theoretical.get(ingredient_id, Decimal("0.000"))),
                    "actual_sale_qty": str(actual.get(ingredient_id, Decimal("0.000"))),
                    "variance_qty": str(
                        self._qty(actual.get(ingredient_id, Decimal("0")) - theoretical.get(ingredient_id, Decimal("0")))
                    ),
                }
                for ingredient_id in ingredient_ids
            ]
        }

    async def reorder_suggestions(
        self,
        *,
        days: int,
        lead_time_days: int = 3,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        from_at = now - timedelta(days=days)
        usage_rows = await self._session.execute(
            select(
                StockMovement.ingredient_id,
                func.coalesce(func.abs(func.sum(StockMovement.quantity_base)), 0),
            )
            .where(
                StockMovement.type == "SALE",
                StockMovement.created_at >= from_at,
                StockMovement.created_at <= now,
            )
            .group_by(StockMovement.ingredient_id)
        )
        usage = {ingredient_id: self._qty(qty) for ingredient_id, qty in usage_rows.all()}

        balance_rows = await self._session.execute(
            select(
                Ingredient.id,
                Ingredient.sku,
                Ingredient.name_en,
                Ingredient.min_stock,
                func.coalesce(func.sum(InventoryBalance.qty_on_hand), 0),
            )
            .outerjoin(InventoryBalance, InventoryBalance.ingredient_id == Ingredient.id)
            .group_by(Ingredient.id, Ingredient.sku, Ingredient.name_en, Ingredient.min_stock)
            .order_by(Ingredient.name_en)
        )

        suggestions: list[dict[str, Any]] = []
        for ingredient_id, sku, name, min_stock, qty_on_hand in balance_rows.all():
            total_usage = usage.get(ingredient_id, Decimal("0.000"))
            avg_daily = self._qty(total_usage / days)
            target_stock = self._qty(Decimal(min_stock) + (avg_daily * lead_time_days))
            reorder_qty = max(Decimal("0.000"), target_stock - self._qty(qty_on_hand))
            if reorder_qty <= 0 and self._qty(qty_on_hand) >= self._qty(min_stock):
                continue
            suggestions.append(
                {
                    "ingredient_id": str(ingredient_id),
                    "sku": sku,
                    "name": name,
                    "qty_on_hand": str(self._qty(qty_on_hand)),
                    "min_stock": str(self._qty(min_stock)),
                    "avg_daily_usage": str(avg_daily),
                    "lead_time_days": lead_time_days,
                    "target_stock": str(target_stock),
                    "suggested_order_qty": str(self._qty(reorder_qty)),
                }
            )

        return {
            "days": days,
            "lead_time_days": lead_time_days,
            "suggestions": suggestions,
        }

    def sales_csv(self, report: dict[str, Any]) -> str:
        rows = [
            ["metric", "value"],
            ["sales_total", report["totals"]["sales_total"]],
            ["order_count", report["totals"]["order_count"]],
            ["avg_ticket", report["totals"]["avg_ticket"]],
            [],
            ["category", "quantity", "sales_total"],
            *[
                [row["category"], row["quantity"], row["sales_total"]]
                for row in report["by_category"]
            ],
            [],
            ["product", "quantity", "sales_total"],
            *[
                [row["product"], row["quantity"], row["sales_total"]]
                for row in report["by_product"]
            ],
            [],
            ["payment_method", "payment_total"],
            *[
                [row["method"], row["payment_total"]]
                for row in report["by_payment"]
            ],
        ]
        return self._write_csv(rows)

    def profit_csv(self, report: dict[str, Any]) -> str:
        rows = [
            ["metric", "value"],
            ["revenue", report["totals"]["revenue"]],
            ["cogs", report["totals"]["cogs"]],
            ["gross_profit", report["totals"]["gross_profit"]],
            ["margin_percent", report["totals"]["margin_percent"]],
            [],
            ["product", "revenue", "cogs", "gross_profit", "margin_percent"],
            *[
                [
                    row["product"],
                    row["revenue"],
                    row["cogs"],
                    row["gross_profit"],
                    row["margin_percent"],
                ]
                for row in report["by_product"]
            ],
            [],
            ["category", "revenue", "cogs", "gross_profit", "margin_percent"],
            *[
                [
                    row["category"],
                    row["revenue"],
                    row["cogs"],
                    row["gross_profit"],
                    row["margin_percent"],
                ]
                for row in report["by_category"]
            ],
        ]
        return self._write_csv(rows)

    async def _count_orders(self, *, from_at: datetime | None, to_at: datetime | None) -> int:
        stmt = select(func.count(distinct(Sale.id))).select_from(Sale).where(
            Sale.status.in_(REPORT_SALE_STATUSES)
        )
        stmt = self._filter_dates(stmt, Sale.created_at, from_at, to_at)
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def _sum_sale_lines(self, *, from_at: datetime | None, to_at: datetime | None) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(SaleItem.line_total), 0))
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.status.in_(REPORT_SALE_STATUSES))
        )
        stmt = self._filter_dates(stmt, Sale.created_at, from_at, to_at)
        result = await self._session.execute(stmt)
        return self._money(result.scalar_one())

    async def _sum_cogs(self, *, from_at: datetime | None, to_at: datetime | None) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(SaleItemConsumption.line_cogs), 0))
            .select_from(SaleItemConsumption)
            .join(SaleItem, SaleItem.id == SaleItemConsumption.sale_item_id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.status.in_(REPORT_SALE_STATUSES))
        )
        stmt = self._filter_dates(stmt, Sale.created_at, from_at, to_at)
        result = await self._session.execute(stmt)
        return self._money(result.scalar_one())

    async def _sales_by_category(
        self,
        *,
        from_at: datetime | None,
        to_at: datetime | None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                Category.id,
                Category.name_en,
                func.coalesce(func.sum(SaleItem.qty), 0),
                func.coalesce(func.sum(SaleItem.line_total), 0),
            )
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(ProductVariant, ProductVariant.id == SaleItem.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .join(Category, Category.id == Product.category_id)
            .where(Sale.status.in_(REPORT_SALE_STATUSES))
            .group_by(Category.id, Category.name_en)
            .order_by(func.sum(SaleItem.line_total).desc())
        )
        stmt = self._filter_dates(stmt, Sale.created_at, from_at, to_at)
        result = await self._session.execute(stmt)
        return [
            {
                "category_id": str(category_id),
                "category": category,
                "quantity": int(quantity or 0),
                "sales_total": str(self._money(total)),
            }
            for category_id, category, quantity, total in result.all()
        ]

    async def _sales_by_product(
        self,
        *,
        from_at: datetime | None,
        to_at: datetime | None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                ProductVariant.id,
                Product.name_en,
                ProductVariant.name_en,
                func.coalesce(func.sum(SaleItem.qty), 0),
                func.coalesce(func.sum(SaleItem.line_total), 0),
            )
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(ProductVariant, ProductVariant.id == SaleItem.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(Sale.status.in_(REPORT_SALE_STATUSES))
            .group_by(ProductVariant.id, Product.name_en, ProductVariant.name_en)
            .order_by(func.sum(SaleItem.line_total).desc())
        )
        stmt = self._filter_dates(stmt, Sale.created_at, from_at, to_at)
        result = await self._session.execute(stmt)
        return [
            {
                "variant_id": str(variant_id),
                "product": f"{product} - {variant}",
                "quantity": int(quantity or 0),
                "sales_total": str(self._money(total)),
            }
            for variant_id, product, variant, quantity, total in result.all()
        ]

    async def _sales_by_payment(
        self,
        *,
        from_at: datetime | None,
        to_at: datetime | None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(Payment.method, func.coalesce(func.sum(Payment.amount), 0))
            .select_from(Payment)
            .join(Sale, Sale.id == Payment.sale_id)
            .where(Sale.status.in_(REPORT_SALE_STATUSES))
            .group_by(Payment.method)
            .order_by(Payment.method)
        )
        stmt = self._filter_dates(stmt, Sale.created_at, from_at, to_at)
        result = await self._session.execute(stmt)
        return [
            {"method": method, "payment_total": str(self._money(total))}
            for method, total in result.all()
        ]

    async def _profit_by_product(
        self,
        *,
        from_at: datetime | None,
        to_at: datetime | None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                ProductVariant.id,
                Product.name_en,
                ProductVariant.name_en,
                func.coalesce(func.sum(SaleItem.line_total), 0),
                func.coalesce(func.sum(SaleItem.cogs), 0),
            )
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(ProductVariant, ProductVariant.id == SaleItem.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(Sale.status.in_(REPORT_SALE_STATUSES))
            .group_by(ProductVariant.id, Product.name_en, ProductVariant.name_en)
            .order_by(func.sum(SaleItem.line_total).desc())
        )
        stmt = self._filter_dates(stmt, Sale.created_at, from_at, to_at)
        result = await self._session.execute(stmt)
        return [
            self._profit_row(
                id_key="variant_id",
                id_value=variant_id,
                name_key="product",
                name=f"{product} - {variant}",
                revenue=revenue,
                cogs=cogs,
            )
            for variant_id, product, variant, revenue, cogs in result.all()
        ]

    async def _profit_by_category(
        self,
        *,
        from_at: datetime | None,
        to_at: datetime | None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                Category.id,
                Category.name_en,
                func.coalesce(func.sum(SaleItem.line_total), 0),
                func.coalesce(func.sum(SaleItem.cogs), 0),
            )
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(ProductVariant, ProductVariant.id == SaleItem.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .join(Category, Category.id == Product.category_id)
            .where(Sale.status.in_(REPORT_SALE_STATUSES))
            .group_by(Category.id, Category.name_en)
            .order_by(func.sum(SaleItem.line_total).desc())
        )
        stmt = self._filter_dates(stmt, Sale.created_at, from_at, to_at)
        result = await self._session.execute(stmt)
        return [
            self._profit_row(
                id_key="category_id",
                id_value=category_id,
                name_key="category",
                name=category,
                revenue=revenue,
                cogs=cogs,
            )
            for category_id, category, revenue, cogs in result.all()
        ]

    def _high_sales_low_margin(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        revenues = [Decimal(row["revenue"]) for row in rows]
        average_revenue = sum(revenues, Decimal("0")) / len(revenues)
        return [
            row
            for row in rows
            if Decimal(row["revenue"]) >= average_revenue
            and Decimal(row["margin_percent"]) < Decimal("30")
        ][:10]

    def _profit_row(
        self,
        *,
        id_key: str,
        id_value: Any,
        name_key: str,
        name: str,
        revenue: Any,
        cogs: Any,
    ) -> dict[str, Any]:
        revenue_decimal = self._money(revenue)
        cogs_decimal = self._money(cogs)
        gross_profit = self._money(revenue_decimal - cogs_decimal)
        return {
            id_key: str(id_value),
            name_key: name,
            "revenue": str(revenue_decimal),
            "cogs": str(cogs_decimal),
            "gross_profit": str(gross_profit),
            "margin_percent": str(self._margin(gross_profit, revenue_decimal)),
        }

    @staticmethod
    def _filter_dates(
        stmt: Select[tuple[Any, ...]],
        column: Any,
        from_at: datetime | None,
        to_at: datetime | None,
    ) -> Select[tuple[Any, ...]]:
        if from_at is not None:
            stmt = stmt.where(column >= from_at)
        if to_at is not None:
            stmt = stmt.where(column <= to_at)
        return stmt

    @staticmethod
    def _money(value: Any) -> Decimal:
        return Decimal(value or 0).quantize(MONEY)

    @staticmethod
    def _qty(value: Any) -> Decimal:
        return Decimal(value or 0).quantize(QTY)

    @staticmethod
    def _margin(gross_profit: Decimal, revenue: Decimal) -> Decimal:
        if revenue == 0:
            return Decimal("0.00")
        return ((gross_profit / revenue) * Decimal("100")).quantize(MONEY)

    @staticmethod
    def _write_csv(rows: list[list[Any]]) -> str:
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerows(rows)
        return buffer.getvalue()

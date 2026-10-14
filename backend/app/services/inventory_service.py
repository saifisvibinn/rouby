from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError, NotFoundError
from app.models.branch import Location
from app.models.catalog import Ingredient
from app.models.inventory import (
    GoodsReceipt,
    GoodsReceiptItem,
    InventoryBalance,
    InventoryBatch,
    PurchaseOrder,
    PurchaseOrderItem,
    StockCount,
    StockCountItem,
    StockMovement,
    WasteRecord,
)

QTY = Decimal("0.001")
COST = Decimal("0.000001")
NEGATIVE_TYPES = {"SALE", "WASTE", "INTERNAL_USE", "TRANSFER_OUT"}


@dataclass(frozen=True)
class BatchAllocation:
    batch_id: UUID
    quantity: Decimal


class InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_purchase_order(
        self,
        *,
        branch_id: UUID,
        supplier_id: UUID | None,
        items: list[dict],
        user_id: UUID | None = None,
        notes: str | None = None,
    ) -> PurchaseOrder:
        order = PurchaseOrder(
            branch_id=branch_id,
            supplier_id=supplier_id,
            created_by_id=user_id,
            notes=notes,
        )
        self._session.add(order)
        await self._session.flush()

        for item in items:
            self._session.add(
                PurchaseOrderItem(
                    purchase_order_id=order.id,
                    ingredient_id=item["ingredient_id"],
                    ordered_qty=self._positive_decimal(item["ordered_qty"], "ordered_qty"),
                    unit_cost=self._non_negative_decimal(item["unit_cost"], "unit_cost"),
                    notes=item.get("notes"),
                )
            )
        await self._session.flush()
        return order

    async def create_goods_receipt(
        self,
        *,
        location_id: UUID,
        items: list[dict],
        supplier_id: UUID | None = None,
        purchase_order_id: UUID | None = None,
        user_id: UUID | None = None,
        notes: str | None = None,
    ) -> GoodsReceipt:
        location = await self._get_location(location_id)
        receipt = GoodsReceipt(
            purchase_order_id=purchase_order_id,
            supplier_id=supplier_id,
            location_id=location.id,
            branch_id=location.branch_id,
            received_by_id=user_id,
            notes=notes,
        )
        self._session.add(receipt)
        await self._session.flush()

        for item in items:
            self._session.add(
                GoodsReceiptItem(
                    receipt_id=receipt.id,
                    purchase_order_item_id=item.get("purchase_order_item_id"),
                    ingredient_id=item["ingredient_id"],
                    received_qty=self._positive_decimal(item["received_qty"], "received_qty"),
                    unit_cost=self._non_negative_decimal(item["unit_cost"], "unit_cost"),
                    expiry_date=item.get("expiry_date"),
                )
            )
        await self._session.flush()
        return await self._load_receipt(receipt.id)

    async def confirm_goods_receipt(
        self,
        receipt_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> GoodsReceipt:
        receipt = await self._load_receipt(receipt_id)
        if receipt.status == "CONFIRMED":
            return receipt
        if receipt.status != "DRAFT":
            raise AppError("INVALID_RECEIPT_STATUS", "Only draft receipts can be confirmed")

        for item in receipt.items:
            await self.apply_purchase_receipt(
                ingredient_id=item.ingredient_id,
                location_id=receipt.location_id,
                received_qty=item.received_qty,
                unit_cost=item.unit_cost,
                expiry_date=item.expiry_date,
                receipt_line_id=item.id,
                user_id=user_id,
                reference_id=receipt.id,
            )

        receipt.status = "CONFIRMED"
        receipt.confirmed_by_id = user_id
        receipt.confirmed_at = datetime.now(UTC)
        await self._session.flush()
        return receipt

    async def post_movement(
        self,
        *,
        type: str,
        ingredient_id: UUID,
        location_id: UUID,
        quantity_base: Decimal,
        unit_cost: Decimal | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        user_id: UUID | None = None,
        reason: str | None = None,
        allow_negative_balance: bool = False,
    ) -> StockMovement:
        quantity = self._non_zero_decimal(quantity_base, "quantity_base")
        location = await self._get_location(location_id)
        balance = await self._lock_balance(ingredient_id, location.id, location.branch_id)
        return await self._post_movement_on_balance(
            balance=balance,
            type=type,
            quantity_base=quantity,
            unit_cost=unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            user_id=user_id,
            reason=reason,
            allow_negative_balance=allow_negative_balance,
        )

    async def apply_purchase_receipt(
        self,
        *,
        ingredient_id: UUID,
        location_id: UUID,
        received_qty: Decimal,
        unit_cost: Decimal,
        expiry_date: date | None = None,
        receipt_line_id: UUID | None = None,
        user_id: UUID | None = None,
        reference_type: str = "goods_receipt",
        reference_id: UUID | None = None,
    ) -> StockMovement:
        quantity = self._positive_decimal(received_qty, "received_qty")
        cost = self._non_negative_decimal(unit_cost, "unit_cost")
        location = await self._get_location(location_id)
        balance = await self._lock_balance(ingredient_id, location.id, location.branch_id)
        ingredient = await self._get_ingredient_for_update(ingredient_id)

        old_qty = Decimal(balance.qty_on_hand)
        total_qty = old_qty + quantity
        if total_qty > 0:
            old_value = old_qty * Decimal(ingredient.wac)
            received_value = quantity * cost
            ingredient.wac = ((old_value + received_value) / total_qty).quantize(COST)

        movement = await self._post_movement_on_balance(
            balance=balance,
            type="PURCHASE_RECEIPT",
            quantity_base=quantity,
            unit_cost=cost,
            reference_type=reference_type,
            reference_id=reference_id or receipt_line_id,
            user_id=user_id,
            reason="Goods receipt",
        )
        await self._upsert_batch(
            ingredient_id=ingredient_id,
            location_id=location.id,
            branch_id=location.branch_id,
            received_qty=quantity,
            expiry_date=expiry_date,
            receipt_line_id=receipt_line_id,
        )
        return movement

    async def apply_waste(
        self,
        *,
        ingredient_id: UUID,
        location_id: UUID,
        quantity_base: Decimal,
        reason: str,
        user_id: UUID | None = None,
    ) -> WasteRecord:
        quantity = self._positive_decimal(quantity_base, "quantity_base")
        location = await self._get_location(location_id)
        record = WasteRecord(
            ingredient_id=ingredient_id,
            location_id=location.id,
            branch_id=location.branch_id,
            quantity_base=quantity,
            reason=reason,
            user_id=user_id,
        )
        self._session.add(record)
        await self._session.flush()

        movement = await self.post_movement(
            type="WASTE",
            ingredient_id=ingredient_id,
            location_id=location.id,
            quantity_base=-quantity,
            reference_type="waste_record",
            reference_id=record.id,
            user_id=user_id,
            reason=reason,
        )
        record.movement_id = movement.id
        await self.allocate_fefo(ingredient_id, location.id, quantity)
        await self._session.flush()
        return record

    async def apply_adjustment(
        self,
        *,
        ingredient_id: UUID,
        location_id: UUID,
        quantity_delta: Decimal,
        reason: str,
        user_id: UUID | None = None,
    ) -> StockMovement:
        return await self.post_movement(
            type="ADJUSTMENT",
            ingredient_id=ingredient_id,
            location_id=location_id,
            quantity_base=self._non_zero_decimal(quantity_delta, "quantity_delta"),
            reference_type="adjustment",
            user_id=user_id,
            reason=reason,
            allow_negative_balance=False,
        )

    async def create_stock_count(
        self,
        *,
        location_id: UUID,
        items: list[dict],
        user_id: UUID | None = None,
        notes: str | None = None,
    ) -> StockCount:
        location = await self._get_location(location_id)
        count = StockCount(
            location_id=location.id,
            branch_id=location.branch_id,
            counted_by_id=user_id,
            notes=notes,
        )
        self._session.add(count)
        await self._session.flush()

        for item in items:
            ingredient_id = item["ingredient_id"]
            balance = await self._lock_balance(ingredient_id, location.id, location.branch_id)
            actual_qty = self._non_negative_decimal(item["actual_qty"], "actual_qty")
            theoretical_qty = Decimal(balance.qty_on_hand)
            self._session.add(
                StockCountItem(
                    stock_count_id=count.id,
                    ingredient_id=ingredient_id,
                    theoretical_qty=theoretical_qty,
                    actual_qty=actual_qty,
                    variance_qty=actual_qty - theoretical_qty,
                )
            )
        await self._session.flush()
        return await self._load_stock_count(count.id)

    async def post_stock_count_variance(
        self,
        stock_count_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> StockCount:
        count = await self._load_stock_count(stock_count_id)
        if count.status == "POSTED":
            return count
        if count.status != "DRAFT":
            raise AppError("INVALID_STOCK_COUNT_STATUS", "Only draft stock counts can be posted")

        for item in count.items:
            if item.variance_qty == 0:
                continue
            movement = await self.post_movement(
                type="COUNT_VARIANCE",
                ingredient_id=item.ingredient_id,
                location_id=count.location_id,
                quantity_base=item.variance_qty,
                reference_type="stock_count",
                reference_id=count.id,
                user_id=user_id,
                reason="Stock count variance",
            )
            item.movement_id = movement.id

        count.status = "POSTED"
        count.posted_by_id = user_id
        count.posted_at = datetime.now(UTC)
        await self._session.flush()
        return count

    async def allocate_fefo(
        self,
        ingredient_id: UUID,
        location_id: UUID,
        qty: Decimal,
        *,
        allow_partial: bool = False,
    ) -> list[BatchAllocation]:
        remaining = self._positive_decimal(qty, "qty")
        location = await self._get_location(location_id)
        result = await self._session.execute(
            select(InventoryBatch)
            .where(
                InventoryBatch.ingredient_id == ingredient_id,
                InventoryBatch.location_id == location.id,
                InventoryBatch.remaining_qty > 0,
            )
            .order_by(
                case((InventoryBatch.expiry_date.is_(None), 1), else_=0),
                InventoryBatch.expiry_date.asc(),
                InventoryBatch.created_at.asc(),
            )
            .with_for_update()
        )
        batches = list(result.scalars().all())
        allocations: list[BatchAllocation] = []
        for batch in batches:
            if remaining <= 0:
                break
            take = min(Decimal(batch.remaining_qty), remaining)
            batch.remaining_qty = (Decimal(batch.remaining_qty) - take).quantize(QTY)
            allocations.append(BatchAllocation(batch_id=batch.id, quantity=take.quantize(QTY)))
            remaining -= take

        if remaining > 0 and not allow_partial:
            raise AppError(
                "INSUFFICIENT_BATCH_STOCK",
                "Not enough batch stock to allocate",
                status_code=status.HTTP_409_CONFLICT,
            )
        await self._session.flush()
        return allocations

    async def rebuild_balances_from_ledger(self) -> dict[tuple[UUID, UUID], Decimal]:
        result = await self._session.execute(
            select(
                StockMovement.ingredient_id,
                StockMovement.location_id,
                func.coalesce(func.sum(StockMovement.quantity_base), 0),
            ).group_by(StockMovement.ingredient_id, StockMovement.location_id)
        )
        expected = {
            (ingredient_id, location_id): Decimal(str(total)).quantize(QTY)
            for ingredient_id, location_id, total in result.all()
        }

        balances = await self._session.execute(select(InventoryBalance))
        actual = {
            (balance.ingredient_id, balance.location_id): Decimal(balance.qty_on_hand).quantize(QTY)
            for balance in balances.scalars().all()
        }
        if actual != expected:
            raise AppError(
                "LEDGER_BALANCE_MISMATCH",
                "Inventory balances do not match stock movement ledger",
                details={
                    "expected": self._stringify_balance_map(expected),
                    "actual": self._stringify_balance_map(actual),
                },
            )
        return expected

    async def list_locations(self, branch_id: UUID | None = None) -> list[Location]:
        query = select(Location).order_by(Location.name_en)
        if branch_id is not None:
            query = query.where(Location.branch_id == branch_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_balances(self) -> list[InventoryBalance]:
        result = await self._session.execute(
            select(InventoryBalance)
            .options(
                selectinload(InventoryBalance.ingredient),
                selectinload(InventoryBalance.location),
            )
            .order_by(InventoryBalance.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_movements(self) -> list[StockMovement]:
        result = await self._session.execute(
            select(StockMovement)
            .options(selectinload(StockMovement.ingredient), selectinload(StockMovement.location))
            .order_by(StockMovement.created_at.desc())
        )
        return list(result.scalars().all())

    async def _post_movement_on_balance(
        self,
        *,
        balance: InventoryBalance,
        type: str,
        quantity_base: Decimal,
        unit_cost: Decimal | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        user_id: UUID | None = None,
        reason: str | None = None,
        allow_negative_balance: bool = False,
    ) -> StockMovement:
        if type in NEGATIVE_TYPES and quantity_base > 0:
            quantity_base = -quantity_base
        new_qty = (Decimal(balance.qty_on_hand) + quantity_base).quantize(QTY)
        if new_qty < 0 and not allow_negative_balance:
            raise AppError(
                "INSUFFICIENT_STOCK",
                "Inventory balance cannot go below zero",
                status_code=status.HTTP_409_CONFLICT,
            )
        movement = StockMovement(
            type=type,
            ingredient_id=balance.ingredient_id,
            location_id=balance.location_id,
            branch_id=balance.branch_id,
            quantity_base=quantity_base.quantize(QTY),
            unit_cost=None if unit_cost is None else Decimal(unit_cost).quantize(COST),
            reference_type=reference_type,
            reference_id=reference_id,
            user_id=user_id,
            reason=reason,
        )
        balance.qty_on_hand = new_qty
        self._session.add(movement)
        await self._session.flush()
        return movement

    async def _lock_balance(
        self,
        ingredient_id: UUID,
        location_id: UUID,
        branch_id: UUID,
    ) -> InventoryBalance:
        result = await self._session.execute(
            select(InventoryBalance)
            .where(
                InventoryBalance.ingredient_id == ingredient_id,
                InventoryBalance.location_id == location_id,
            )
            .with_for_update()
        )
        balance = result.scalar_one_or_none()
        if balance is not None:
            return balance
        balance = InventoryBalance(
            ingredient_id=ingredient_id,
            location_id=location_id,
            branch_id=branch_id,
            qty_on_hand=Decimal("0"),
        )
        self._session.add(balance)
        await self._session.flush()
        return balance

    async def _upsert_batch(
        self,
        *,
        ingredient_id: UUID,
        location_id: UUID,
        branch_id: UUID,
        received_qty: Decimal,
        expiry_date: date | None,
        receipt_line_id: UUID | None,
    ) -> InventoryBatch:
        batch: InventoryBatch | None = None
        if receipt_line_id is not None:
            result = await self._session.execute(
                select(InventoryBatch)
                .where(InventoryBatch.receipt_line_id == receipt_line_id)
                .with_for_update()
            )
            batch = result.scalar_one_or_none()

        if batch is None:
            batch = InventoryBatch(
                ingredient_id=ingredient_id,
                location_id=location_id,
                branch_id=branch_id,
                received_qty=received_qty.quantize(QTY),
                remaining_qty=received_qty.quantize(QTY),
                expiry_date=expiry_date,
                receipt_line_id=receipt_line_id,
            )
            self._session.add(batch)
        else:
            batch.received_qty = (Decimal(batch.received_qty) + received_qty).quantize(QTY)
            batch.remaining_qty = (Decimal(batch.remaining_qty) + received_qty).quantize(QTY)
        await self._session.flush()
        return batch

    async def _get_location(self, location_id: UUID) -> Location:
        location = await self._session.get(Location, location_id)
        if location is None:
            raise NotFoundError("Location not found")
        return location

    async def _get_ingredient_for_update(self, ingredient_id: UUID) -> Ingredient:
        result = await self._session.execute(
            select(Ingredient).where(Ingredient.id == ingredient_id).with_for_update()
        )
        ingredient = result.scalar_one_or_none()
        if ingredient is None:
            raise NotFoundError("Ingredient not found")
        return ingredient

    async def _load_receipt(self, receipt_id: UUID) -> GoodsReceipt:
        result = await self._session.execute(
            select(GoodsReceipt)
            .where(GoodsReceipt.id == receipt_id)
            .options(selectinload(GoodsReceipt.items))
        )
        receipt = result.scalar_one_or_none()
        if receipt is None:
            raise NotFoundError("Goods receipt not found")
        return receipt

    async def _load_stock_count(self, stock_count_id: UUID) -> StockCount:
        result = await self._session.execute(
            select(StockCount)
            .where(StockCount.id == stock_count_id)
            .options(selectinload(StockCount.items))
        )
        count = result.scalar_one_or_none()
        if count is None:
            raise NotFoundError("Stock count not found")
        return count

    @staticmethod
    def _positive_decimal(value: Decimal, field: str) -> Decimal:
        amount = Decimal(value).quantize(QTY)
        if amount <= 0:
            raise AppError("INVALID_QUANTITY", f"{field} must be positive", status_code=422)
        return amount

    @staticmethod
    def _non_negative_decimal(value: Decimal, field: str) -> Decimal:
        amount = Decimal(value)
        if amount < 0:
            raise AppError("INVALID_AMOUNT", f"{field} cannot be negative", status_code=422)
        return amount.quantize(COST)

    @staticmethod
    def _non_zero_decimal(value: Decimal, field: str) -> Decimal:
        amount = Decimal(value).quantize(QTY)
        if amount == 0:
            raise AppError("INVALID_QUANTITY", f"{field} cannot be zero", status_code=422)
        return amount

    @staticmethod
    def _stringify_balance_map(rows: dict[tuple[UUID, UUID], Decimal]) -> dict[str, str]:
        return {
            f"{ingredient_id}:{location_id}": str(qty)
            for (ingredient_id, location_id), qty in rows.items()
        }

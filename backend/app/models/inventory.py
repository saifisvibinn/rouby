from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

STOCK_MOVEMENT_TYPES = (
    "PURCHASE_RECEIPT",
    "SALE",
    "SALE_REVERSAL",
    "WASTE",
    "INTERNAL_USE",
    "ADJUSTMENT",
    "COUNT_VARIANCE",
    "RETURN_TO_STOCK",
    "TRANSFER_IN",
    "TRANSFER_OUT",
)


class InventoryBalance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint("ingredient_id", "location_id", name="uq_inventory_balance_item_location"),
    )

    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    location_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True
    )
    qty_on_hand: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0")
    )

    ingredient = relationship("Ingredient")
    location = relationship("Location")
    branch = relationship("Branch")


class PurchaseOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "purchase_orders"

    supplier_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True, index=True
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    items: Mapped[list[PurchaseOrderItem]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'ORDERED', 'PARTIALLY_RECEIVED', 'RECEIVED', 'CANCELLED')",
            name="ck_purchase_orders_status",
        ),
    )


class PurchaseOrderItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "purchase_order_items"

    purchase_order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    ingredient = relationship("Ingredient")

    __table_args__ = (
        CheckConstraint("ordered_qty > 0", name="ck_purchase_order_items_qty_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_purchase_order_items_cost_nonneg"),
    )


class GoodsReceipt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "goods_receipts"

    purchase_order_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True, index=True
    )
    supplier_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True, index=True
    )
    location_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    received_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    confirmed_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[GoodsReceiptItem]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')",
            name="ck_goods_receipts_status",
        ),
    )


class GoodsReceiptItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "goods_receipt_items"

    receipt_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("goods_receipts.id"), nullable=False, index=True
    )
    purchase_order_item_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("purchase_order_items.id"), nullable=True, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    received_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    receipt: Mapped[GoodsReceipt] = relationship(back_populates="items")
    ingredient = relationship("Ingredient")

    __table_args__ = (
        CheckConstraint("received_qty > 0", name="ck_goods_receipt_items_qty_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_goods_receipt_items_cost_nonneg"),
    )


class InventoryBatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inventory_batches"

    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    location_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True
    )
    received_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    remaining_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    receipt_line_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("goods_receipt_items.id"), nullable=True, index=True
    )

    ingredient = relationship("Ingredient")
    location = relationship("Location")
    receipt_line = relationship("GoodsReceiptItem")

    __table_args__ = (
        CheckConstraint("received_qty >= 0", name="ck_inventory_batches_received_nonneg"),
        CheckConstraint("remaining_qty >= 0", name="ck_inventory_batches_remaining_nonneg"),
    )


class StockMovement(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "stock_movements"

    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    location_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True
    )
    quantity_base: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reference_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ingredient = relationship("Ingredient")
    location = relationship("Location")
    branch = relationship("Branch")
    user = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "type IN ("
            "'PURCHASE_RECEIPT', 'SALE', 'SALE_REVERSAL', 'WASTE', 'INTERNAL_USE', "
            "'ADJUSTMENT', 'COUNT_VARIANCE', 'RETURN_TO_STOCK', 'TRANSFER_IN', 'TRANSFER_OUT'"
            ")",
            name="ck_stock_movements_type",
        ),
        CheckConstraint("quantity_base <> 0", name="ck_stock_movements_qty_nonzero"),
    )


class WasteRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "waste_records"

    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    location_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True
    )
    quantity_base: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    movement_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stock_movements.id"), nullable=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    movement = relationship("StockMovement")

    __table_args__ = (CheckConstraint("quantity_base > 0", name="ck_waste_records_qty_positive"),)


class StockCount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "stock_counts"

    location_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    counted_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    posted_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[StockCountItem]] = relationship(
        back_populates="stock_count", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'POSTED', 'CANCELLED')",
            name="ck_stock_counts_status",
        ),
    )


class StockCountItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "stock_count_items"
    __table_args__ = (
        UniqueConstraint("stock_count_id", "ingredient_id", name="uq_stock_count_item_ingredient"),
        CheckConstraint("theoretical_qty >= 0", name="ck_stock_count_items_theoretical_nonneg"),
        CheckConstraint("actual_qty >= 0", name="ck_stock_count_items_actual_nonneg"),
    )

    stock_count_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stock_counts.id"), nullable=False, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    theoretical_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    actual_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    variance_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    movement_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stock_movements.id"), nullable=True
    )

    stock_count: Mapped[StockCount] = relationship(back_populates="items")
    ingredient = relationship("Ingredient")
    movement = relationship("StockMovement")


class SupplierIngredientPrice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "supplier_ingredient_prices"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            "ingredient_id",
            "unit_id",
            "effective_from",
            name="uq_supplier_ingredient_price_effective",
        ),
        CheckConstraint("price >= 0", name="ck_supplier_ingredient_prices_price_nonneg"),
    )

    supplier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("units.id"), nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)

    supplier = relationship("Supplier")
    ingredient = relationship("Ingredient")
    unit = relationship("Unit")


def _prevent_stock_movement_update(_mapper, _connection, _target) -> None:
    raise ValueError("StockMovement is append-only")


event.listen(StockMovement, "before_update", _prevent_stock_movement_update)
event.listen(StockMovement, "before_delete", _prevent_stock_movement_update)

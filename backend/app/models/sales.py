from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Sale(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'PREPARING', 'COMPLETED', 'CANCELLED')",
            name="ck_sales_status",
        ),
        CheckConstraint(
            "order_type IN ('dine_in', 'takeaway')",
            name="ck_sales_order_type",
        ),
        CheckConstraint("subtotal >= 0", name="ck_sales_subtotal_nonneg"),
        CheckConstraint("discount >= 0", name="ck_sales_discount_nonneg"),
        CheckConstraint("tax >= 0", name="ck_sales_tax_nonneg"),
        CheckConstraint("total >= 0", name="ck_sales_total_nonneg"),
        CheckConstraint("cogs_total >= 0", name="ck_sales_cogs_nonneg"),
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, default="dine_in")
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    cogs_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    flagged_negative_stock: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    items: Mapped[list[SaleItem]] = relationship(
        back_populates="sale", cascade="all, delete-orphan"
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="sale", cascade="all, delete-orphan"
    )


class SaleItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_sale_items_qty_positive"),
        CheckConstraint("unit_price >= 0", name="ck_sale_items_price_nonneg"),
        CheckConstraint("line_total >= 0", name="ck_sale_items_line_total_nonneg"),
        CheckConstraint("cogs >= 0", name="ck_sale_items_cogs_nonneg"),
    )

    sale_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sales.id"), nullable=False, index=True
    )
    variant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_variants.id"),
        nullable=False,
        index=True,
    )
    recipe_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("recipe_versions.id"), nullable=True
    )
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cogs: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )

    sale: Mapped[Sale] = relationship(back_populates="items")
    variant = relationship("ProductVariant")
    modifiers: Mapped[list[SaleItemModifier]] = relationship(
        back_populates="sale_item", cascade="all, delete-orphan"
    )
    consumptions: Mapped[list[SaleItemConsumption]] = relationship(
        back_populates="sale_item", cascade="all, delete-orphan"
    )


class SaleItemModifier(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sale_item_modifiers"

    sale_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sale_items.id"), nullable=False, index=True
    )
    modifier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("modifiers.id"), nullable=False, index=True
    )
    price_delta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )

    sale_item: Mapped[SaleItem] = relationship(back_populates="modifiers")
    modifier = relationship("Modifier")


class SaleItemConsumption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sale_item_consumptions"
    __table_args__ = (
        CheckConstraint("qty_base > 0", name="ck_sale_item_cons_qty_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_sale_item_cons_cost_nonneg"),
        CheckConstraint("line_cogs >= 0", name="ck_sale_item_cons_cogs_nonneg"),
    )

    sale_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sale_items.id"), nullable=False, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    qty_base: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    line_cogs: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    sale_item: Mapped[SaleItem] = relationship(back_populates="consumptions")
    ingredient = relationship("Ingredient")


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "method IN ('CASH', 'CARD', 'WALLET')",
            name="ck_payments_method",
        ),
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )

    sale_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sales.id"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="payments")


class IdempotencyKey(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    response_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

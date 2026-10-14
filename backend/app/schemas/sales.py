from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SaleItemModifierIn(BaseModel):
    modifier_id: UUID


class SaleItemIn(BaseModel):
    variant_id: UUID
    qty: int = Field(gt=0)
    modifier_ids: list[UUID] = Field(default_factory=list)
    notes: str | None = None


class SaleCreate(BaseModel):
    order_type: str = "dine_in"
    items: list[SaleItemIn] = Field(min_length=1)
    discount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class SaleUpdate(BaseModel):
    order_type: str | None = None
    items: list[SaleItemIn] | None = None
    discount: Decimal | None = Field(default=None, ge=Decimal("0"))


class StatusUpdate(BaseModel):
    status: str


class LineDisposition(BaseModel):
    sale_item_id: UUID
    action: str = "waste"


class CancelRequest(BaseModel):
    line_dispositions: list[LineDisposition] = Field(default_factory=list)


class PaymentIn(BaseModel):
    method: str
    amount: Decimal = Field(gt=0)


class SaleItemModifierOut(BaseModel):
    id: UUID
    modifier_id: UUID
    price_delta: Decimal

    model_config = {"from_attributes": True}


class SaleItemConsumptionOut(BaseModel):
    id: UUID
    ingredient_id: UUID
    qty_base: Decimal
    unit_cost: Decimal
    line_cogs: Decimal

    model_config = {"from_attributes": True}


class SaleItemOut(BaseModel):
    id: UUID
    variant_id: UUID
    recipe_version_id: UUID | None
    qty: int
    unit_price: Decimal
    line_total: Decimal
    notes: str | None
    cogs: Decimal
    modifiers: list[SaleItemModifierOut] = []
    consumptions: list[SaleItemConsumptionOut] = []

    model_config = {"from_attributes": True}


class PaymentOut(BaseModel):
    id: UUID
    sale_id: UUID
    method: str
    amount: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class SaleOut(BaseModel):
    id: UUID
    status: str
    order_type: str
    branch_id: UUID
    user_id: UUID
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    cogs_total: Decimal
    flagged_negative_stock: bool
    items: list[SaleItemOut] = []
    payments: list[PaymentOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class LocationOut(BaseModel):
    id: UUID
    branch_id: UUID
    code: str
    name_en: str
    name_ar: str
    is_active: bool

    model_config = {"from_attributes": True}


class PurchaseOrderItemIn(BaseModel):
    ingredient_id: UUID
    ordered_qty: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    notes: str | None = None


class PurchaseOrderCreate(BaseModel):
    branch_id: UUID
    supplier_id: UUID | None = None
    notes: str | None = None
    items: list[PurchaseOrderItemIn]


class GoodsReceiptItemIn(BaseModel):
    ingredient_id: UUID
    received_qty: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    expiry_date: date | None = None
    purchase_order_item_id: UUID | None = None


class GoodsReceiptCreate(BaseModel):
    location_id: UUID
    supplier_id: UUID | None = None
    purchase_order_id: UUID | None = None
    notes: str | None = None
    confirm: bool = False
    items: list[GoodsReceiptItemIn]


class GoodsReceiptItemOut(BaseModel):
    id: UUID
    ingredient_id: UUID
    received_qty: Decimal
    unit_cost: Decimal
    expiry_date: date | None

    model_config = {"from_attributes": True}


class GoodsReceiptOut(BaseModel):
    id: UUID
    location_id: UUID
    branch_id: UUID
    status: str
    confirmed_at: datetime | None
    items: list[GoodsReceiptItemOut]

    model_config = {"from_attributes": True}


class WasteCreate(BaseModel):
    ingredient_id: UUID
    location_id: UUID
    quantity_base: Decimal = Field(gt=0)
    reason: str = Field(min_length=1)


class WasteOut(BaseModel):
    id: UUID
    ingredient_id: UUID
    location_id: UUID
    branch_id: UUID
    quantity_base: Decimal
    reason: str
    movement_id: UUID | None

    model_config = {"from_attributes": True}


class StockCountItemIn(BaseModel):
    ingredient_id: UUID
    actual_qty: Decimal = Field(ge=0)


class StockCountCreate(BaseModel):
    location_id: UUID
    notes: str | None = None
    post: bool = False
    items: list[StockCountItemIn]


class StockCountItemOut(BaseModel):
    id: UUID
    ingredient_id: UUID
    theoretical_qty: Decimal
    actual_qty: Decimal
    variance_qty: Decimal
    movement_id: UUID | None

    model_config = {"from_attributes": True}


class StockCountOut(BaseModel):
    id: UUID
    location_id: UUID
    branch_id: UUID
    status: str
    posted_at: datetime | None
    items: list[StockCountItemOut]

    model_config = {"from_attributes": True}


class InventoryBalanceOut(BaseModel):
    id: UUID
    ingredient_id: UUID
    location_id: UUID
    branch_id: UUID
    qty_on_hand: Decimal

    model_config = {"from_attributes": True}


class StockMovementOut(BaseModel):
    id: UUID
    type: str
    ingredient_id: UUID
    location_id: UUID
    branch_id: UUID
    quantity_base: Decimal
    unit_cost: Decimal | None
    reference_type: str | None
    reference_id: UUID | None
    user_id: UUID | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

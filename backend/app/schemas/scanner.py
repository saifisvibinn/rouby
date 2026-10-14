from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ScannerMode = Literal["CASHIER", "RECEIVE", "COUNT", "WASTE"]


class ScannerSessionCreate(BaseModel):
    station_id: UUID
    mode: ScannerMode = "CASHIER"
    expires_hours: int = Field(default=12, ge=1, le=12)


class ScannerSessionCreateResponse(BaseModel):
    session_id: UUID
    pairing_token: str
    pairing_expires_at: datetime
    qr_path: str


class ScannerPairRequest(BaseModel):
    pairing_token: str


class ScannerPairResponse(BaseModel):
    session_id: UUID
    device_token: str
    mode: ScannerMode
    expires_at: datetime


class ScanResolveResponse(BaseModel):
    type: Literal["variant", "ingredient", "batch"]
    id: UUID
    code: str
    sku: str | None = None
    name_en: str
    name_ar: str
    price: Decimal | None = None
    ingredient_id: UUID | None = None
    remaining_qty: Decimal | None = None


class ScanEventRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=128)
    qty: int = Field(default=1, ge=1, le=999)
    pin: str | None = Field(default=None, max_length=128)


class ScanEventResponse(BaseModel):
    event_id: str
    duplicate: bool = False
    session_id: UUID
    mode: ScannerMode
    resolved: ScanResolveResponse | None = None
    sale_id: UUID | None = None
    message: str

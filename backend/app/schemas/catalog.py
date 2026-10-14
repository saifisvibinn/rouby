from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: UUID
    code: str
    name_en: str
    name_ar: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class SupplierOut(BaseModel):
    id: UUID
    code: str
    name_en: str
    name_ar: str
    is_active: bool

    model_config = {"from_attributes": True}


class RecipeCostOut(BaseModel):
    variant_id: UUID
    theoretical_cost: Decimal


class UnitOut(BaseModel):
    id: UUID
    code: str
    name_en: str
    name_ar: str
    dimension: str
    factor_to_base: Decimal
    is_base: bool

    model_config = {"from_attributes": True}


class IngredientCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name_en: str = Field(min_length=1, max_length=128)
    name_ar: str = Field(min_length=1, max_length=128)
    storage_unit_id: UUID
    purchase_unit_id: UUID
    wac: Decimal = Field(ge=Decimal("0"))
    min_stock: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    density_g_per_ml: Decimal | None = Field(default=None, gt=Decimal("0"))
    barcode: str | None = Field(default=None, max_length=64)
    default_supplier_id: UUID | None = None
    default_location_id: UUID | None = None


class IngredientOut(IngredientCreate):
    id: UUID
    is_active: bool

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name_en: str = Field(min_length=1, max_length=128)
    name_ar: str = Field(min_length=1, max_length=128)
    category_id: UUID
    image_url: str | None = Field(default=None, max_length=512)
    sort_order: int = 0


class ProductOut(ProductCreate):
    id: UUID
    is_active: bool

    model_config = {"from_attributes": True}


class VariantCreate(BaseModel):
    product_id: UUID
    sku: str = Field(min_length=1, max_length=64)
    name_en: str = Field(min_length=1, max_length=64)
    name_ar: str = Field(min_length=1, max_length=64)
    price: Decimal = Field(ge=Decimal("0"))
    barcode: str | None = Field(default=None, max_length=64)


class VariantOut(VariantCreate):
    id: UUID
    is_active: bool

    model_config = {"from_attributes": True}


class RecipeItemIn(BaseModel):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=Decimal("0"))
    unit_id: UUID


class RecipeCreate(BaseModel):
    variant_id: UUID
    items: list[RecipeItemIn] = Field(min_length=1)


class RecipeItemOut(BaseModel):
    id: UUID
    ingredient_id: UUID
    quantity: Decimal
    unit_id: UUID

    model_config = {"from_attributes": True}


class RecipeVersionOut(BaseModel):
    id: UUID
    variant_id: UUID
    version_number: int
    effective_from: datetime
    is_active: bool
    items: list[RecipeItemOut]

    model_config = {"from_attributes": True}

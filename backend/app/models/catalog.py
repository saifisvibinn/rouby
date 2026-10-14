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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import SoftActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Unit(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "units"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[str] = mapped_column(String(16), nullable=False)  # mass|volume|count
    factor_to_base: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    is_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "dimension IN ('mass', 'volume', 'count')",
            name="ck_units_dimension",
        ),
        CheckConstraint("factor_to_base > 0", name="ck_units_factor_positive"),
    )


class Supplier(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "suppliers"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Ingredient(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "ingredients"

    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("units.id"), nullable=False, index=True
    )
    purchase_unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("units.id"), nullable=False, index=True
    )
    # Current WAC in EGP per base/storage unit
    wac: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=Decimal("0"))
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("0"))
    density_g_per_ml: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    default_supplier_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True
    )
    default_location_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )

    storage_unit: Mapped[Unit] = relationship(foreign_keys=[storage_unit_id])
    purchase_unit: Mapped[Unit] = relationship(foreign_keys=[purchase_unit_id])

    __table_args__ = (CheckConstraint("wac >= 0", name="ck_ingredients_wac_nonneg"),)


class IngredientUnitConversion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pack conversions e.g. 1 tub = 80 scoops for a specific ingredient."""

    __tablename__ = "ingredient_unit_conversions"
    __table_args__ = (
        UniqueConstraint(
            "ingredient_id",
            "from_unit_id",
            "to_unit_id",
            name="uq_ingredient_unit_conv",
        ),
        CheckConstraint("factor > 0", name="ck_ing_conv_factor_positive"),
    )

    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    from_unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("units.id"), nullable=False
    )
    to_unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("units.id"), nullable=False
    )
    factor: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(128), nullable=False)
    category_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=False, index=True
    )
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    category: Mapped[Category] = relationship()
    variants: Mapped[list[ProductVariant]] = relationship(back_populates="product")


class ProductVariant(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "sku", name="uq_variant_product_sku"),
        CheckConstraint("price >= 0", name="ck_variant_price_nonneg"),
    )

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name_en: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    product: Mapped[Product] = relationship(back_populates="variants")
    recipe_versions: Mapped[list[RecipeVersion]] = relationship(back_populates="variant")


class RecipeVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recipe_versions"
    __table_args__ = (
        UniqueConstraint("variant_id", "version_number", name="uq_recipe_variant_version"),
    )

    variant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    variant: Mapped[ProductVariant] = relationship(back_populates="recipe_versions")
    items: Mapped[list[RecipeItem]] = relationship(back_populates="recipe_version")


class RecipeItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recipe_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_recipe_item_qty_positive"),)

    recipe_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("recipe_versions.id"), nullable=False, index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("units.id"), nullable=False
    )

    recipe_version: Mapped[RecipeVersion] = relationship(back_populates="items")
    ingredient: Mapped[Ingredient] = relationship()
    unit: Mapped[Unit] = relationship()


class ModifierGroup(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "modifier_groups"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(64), nullable=False)
    min_select: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_select: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ProductModifierGroup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_modifier_groups"
    __table_args__ = (
        UniqueConstraint("product_id", "modifier_group_id", name="uq_product_mod_group"),
    )

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    modifier_group_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("modifier_groups.id"), nullable=False, index=True
    )


class Modifier(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "modifiers"
    __table_args__ = (CheckConstraint("price_delta >= 0", name="ck_modifier_price_nonneg"),)

    modifier_group_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("modifier_groups.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name_en: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(64), nullable=False)
    price_delta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )

    effects: Mapped[list[ModifierEffect]] = relationship(back_populates="modifier")


class ModifierEffect(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "modifier_effects"
    __table_args__ = (
        CheckConstraint(
            "effect_type IN ('ADD', 'REMOVE', 'REPLACE', 'MULTIPLY')",
            name="ck_modifier_effect_type",
        ),
    )

    modifier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("modifiers.id"), nullable=False, index=True
    )
    effect_type: Mapped[str] = mapped_column(String(16), nullable=False)
    ingredient_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=True
    )
    replace_with_ingredient_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=True
    )
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    unit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("units.id"), nullable=True
    )
    multiply_factor: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)

    modifier: Mapped[Modifier] = relationship(back_populates="effects")

"""phase1 catalog: units, products, recipes, modifiers

Revision ID: 0002_phase1_catalog
Revises: 0001_phase0
Create Date: 2026-10-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase1_catalog"
down_revision: str | None = "0001_phase0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def _active() -> sa.Column:
    return sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"))


def upgrade() -> None:
    op.create_table(
        "units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("dimension", sa.String(16), nullable=False),
        sa.Column("factor_to_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("is_base", sa.Boolean(), nullable=False),
        _active(),
        *_timestamps(),
        sa.CheckConstraint(
            "dimension IN ('mass', 'volume', 'count')",
            name="ck_units_dimension",
        ),
        sa.CheckConstraint("factor_to_base > 0", name="ck_units_factor_positive"),
        sa.UniqueConstraint("code", name="uq_units_code"),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        _active(),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_suppliers_code"),
    )

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        _active(),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_categories_code"),
    )

    op.create_table(
        "ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name_en", sa.String(128), nullable=False),
        sa.Column("name_ar", sa.String(128), nullable=False),
        sa.Column("storage_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wac", sa.Numeric(14, 6), nullable=False),
        sa.Column("min_stock", sa.Numeric(14, 3), nullable=False),
        sa.Column("density_g_per_ml", sa.Numeric(14, 6), nullable=True),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("default_supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("default_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        _active(),
        *_timestamps(),
        sa.CheckConstraint("wac >= 0", name="ck_ingredients_wac_nonneg"),
        sa.ForeignKeyConstraint(["default_location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["default_supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["purchase_unit_id"], ["units.id"]),
        sa.ForeignKeyConstraint(["storage_unit_id"], ["units.id"]),
        sa.UniqueConstraint("barcode", name="uq_ingredients_barcode"),
        sa.UniqueConstraint("sku", name="uq_ingredients_sku"),
    )
    op.create_index("ix_ingredients_purchase_unit_id", "ingredients", ["purchase_unit_id"])
    op.create_index("ix_ingredients_storage_unit_id", "ingredients", ["storage_unit_id"])

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name_en", sa.String(128), nullable=False),
        sa.Column("name_ar", sa.String(128), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        _active(),
        *_timestamps(),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])

    op.create_table(
        "ingredient_unit_conversions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factor", sa.Numeric(18, 6), nullable=False),
        sa.Column("notes", sa.String(255), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("factor > 0", name="ck_ing_conv_factor_positive"),
        sa.ForeignKeyConstraint(["from_unit_id"], ["units.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["to_unit_id"], ["units.id"]),
        sa.UniqueConstraint(
            "ingredient_id",
            "from_unit_id",
            "to_unit_id",
            name="uq_ingredient_unit_conv",
        ),
    )
    op.create_index(
        "ix_ingredient_unit_conversions_ingredient_id",
        "ingredient_unit_conversions",
        ["ingredient_id"],
    )

    op.create_table(
        "product_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("barcode", sa.String(64), nullable=True),
        _active(),
        *_timestamps(),
        sa.CheckConstraint("price >= 0", name="ck_variant_price_nonneg"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.UniqueConstraint("barcode", name="uq_product_variants_barcode"),
        sa.UniqueConstraint("product_id", "sku", name="uq_variant_product_sku"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])

    op.create_table(
        "modifier_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("min_select", sa.Integer(), nullable=False),
        sa.Column("max_select", sa.Integer(), nullable=False),
        _active(),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_modifier_groups_code"),
    )

    op.create_table(
        "recipe_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.UniqueConstraint("variant_id", "version_number", name="uq_recipe_variant_version"),
    )
    op.create_index("ix_recipe_versions_variant_id", "recipe_versions", ["variant_id"])

    op.create_table(
        "product_modifier_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modifier_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["modifier_group_id"], ["modifier_groups.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.UniqueConstraint("product_id", "modifier_group_id", name="uq_product_mod_group"),
    )
    op.create_index(
        "ix_product_modifier_groups_modifier_group_id",
        "product_modifier_groups",
        ["modifier_group_id"],
    )
    op.create_index(
        "ix_product_modifier_groups_product_id",
        "product_modifier_groups",
        ["product_id"],
    )

    op.create_table(
        "modifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("modifier_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("price_delta", sa.Numeric(12, 2), nullable=False),
        _active(),
        *_timestamps(),
        sa.CheckConstraint("price_delta >= 0", name="ck_modifier_price_nonneg"),
        sa.ForeignKeyConstraint(["modifier_group_id"], ["modifier_groups.id"]),
    )
    op.create_index("ix_modifiers_modifier_group_id", "modifiers", ["modifier_group_id"])

    op.create_table(
        "recipe_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("recipe_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("quantity > 0", name="ck_recipe_item_qty_positive"),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["recipe_version_id"], ["recipe_versions.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
    )
    op.create_index("ix_recipe_items_ingredient_id", "recipe_items", ["ingredient_id"])
    op.create_index("ix_recipe_items_recipe_version_id", "recipe_items", ["recipe_version_id"])

    op.create_table(
        "modifier_effects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("modifier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("effect_type", sa.String(16), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("replace_with_ingredient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=True),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("multiply_factor", sa.Numeric(14, 6), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "effect_type IN ('ADD', 'REMOVE', 'REPLACE', 'MULTIPLY')",
            name="ck_modifier_effect_type",
        ),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["modifier_id"], ["modifiers.id"]),
        sa.ForeignKeyConstraint(["replace_with_ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
    )
    op.create_index("ix_modifier_effects_modifier_id", "modifier_effects", ["modifier_id"])


def downgrade() -> None:
    op.drop_index("ix_modifier_effects_modifier_id", table_name="modifier_effects")
    op.drop_table("modifier_effects")
    op.drop_index("ix_recipe_items_recipe_version_id", table_name="recipe_items")
    op.drop_index("ix_recipe_items_ingredient_id", table_name="recipe_items")
    op.drop_table("recipe_items")
    op.drop_index("ix_modifiers_modifier_group_id", table_name="modifiers")
    op.drop_table("modifiers")
    op.drop_index("ix_product_modifier_groups_product_id", table_name="product_modifier_groups")
    op.drop_index(
        "ix_product_modifier_groups_modifier_group_id",
        table_name="product_modifier_groups",
    )
    op.drop_table("product_modifier_groups")
    op.drop_index("ix_recipe_versions_variant_id", table_name="recipe_versions")
    op.drop_table("recipe_versions")
    op.drop_table("modifier_groups")
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index(
        "ix_ingredient_unit_conversions_ingredient_id",
        table_name="ingredient_unit_conversions",
    )
    op.drop_table("ingredient_unit_conversions")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_ingredients_storage_unit_id", table_name="ingredients")
    op.drop_index("ix_ingredients_purchase_unit_id", table_name="ingredients")
    op.drop_table("ingredients")
    op.drop_table("categories")
    op.drop_table("suppliers")
    op.drop_table("units")

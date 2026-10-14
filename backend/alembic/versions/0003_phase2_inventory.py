"""phase2 inventory core

Revision ID: 0003_phase2_inventory
Revises: 0002_phase1_catalog
Create Date: 2026-10-15

"""

# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase2_inventory"
down_revision: str | None = "0002_phase1_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_pk() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def active_col() -> sa.Column:
    return sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"))


def upgrade() -> None:
    _create_inventory_tables()


def downgrade() -> None:
    for index_name, table_name in [
        ("ix_supplier_ingredient_prices_unit_id", "supplier_ingredient_prices"),
        ("ix_supplier_ingredient_prices_ingredient_id", "supplier_ingredient_prices"),
        ("ix_supplier_ingredient_prices_supplier_id", "supplier_ingredient_prices"),
        ("ix_stock_count_items_ingredient_id", "stock_count_items"),
        ("ix_stock_count_items_stock_count_id", "stock_count_items"),
        ("ix_stock_counts_location_id", "stock_counts"),
        ("ix_stock_counts_branch_id", "stock_counts"),
        ("ix_waste_records_location_id", "waste_records"),
        ("ix_waste_records_ingredient_id", "waste_records"),
        ("ix_waste_records_branch_id", "waste_records"),
        ("ix_stock_movements_user_id", "stock_movements"),
        ("ix_stock_movements_type", "stock_movements"),
        ("ix_stock_movements_reference_type", "stock_movements"),
        ("ix_stock_movements_reference_id", "stock_movements"),
        ("ix_stock_movements_location_id", "stock_movements"),
        ("ix_stock_movements_ingredient_id", "stock_movements"),
        ("ix_stock_movements_branch_id", "stock_movements"),
        ("ix_inventory_batches_receipt_line_id", "inventory_batches"),
        ("ix_inventory_batches_location_id", "inventory_batches"),
        ("ix_inventory_batches_ingredient_id", "inventory_batches"),
        ("ix_inventory_batches_branch_id", "inventory_batches"),
        ("ix_inventory_balances_location_id", "inventory_balances"),
        ("ix_inventory_balances_ingredient_id", "inventory_balances"),
        ("ix_inventory_balances_branch_id", "inventory_balances"),
        ("ix_goods_receipt_items_receipt_id", "goods_receipt_items"),
        ("ix_goods_receipt_items_purchase_order_item_id", "goods_receipt_items"),
        ("ix_goods_receipt_items_ingredient_id", "goods_receipt_items"),
        ("ix_goods_receipts_supplier_id", "goods_receipts"),
        ("ix_goods_receipts_purchase_order_id", "goods_receipts"),
        ("ix_goods_receipts_location_id", "goods_receipts"),
        ("ix_goods_receipts_branch_id", "goods_receipts"),
        ("ix_purchase_order_items_purchase_order_id", "purchase_order_items"),
        ("ix_purchase_order_items_ingredient_id", "purchase_order_items"),
        ("ix_purchase_orders_supplier_id", "purchase_orders"),
        ("ix_purchase_orders_branch_id", "purchase_orders"),
    ]:
        op.drop_index(index_name, table_name=table_name)

    for table_name in [
        "supplier_ingredient_prices",
        "stock_count_items",
        "stock_counts",
        "waste_records",
        "stock_movements",
        "inventory_batches",
        "inventory_balances",
        "goods_receipt_items",
        "goods_receipts",
        "purchase_order_items",
        "purchase_orders",
    ]:
        op.drop_table(table_name)

def _create_catalog_tables() -> None:
    op.create_table(
        "units",
        uuid_pk(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("dimension", sa.String(16), nullable=False),
        sa.Column("factor_to_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("is_base", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        active_col(),
        *timestamps(),
        sa.CheckConstraint("dimension IN ('mass', 'volume', 'count')", name="ck_units_dimension"),
        sa.CheckConstraint("factor_to_base > 0", name="ck_units_factor_positive"),
        sa.UniqueConstraint("code", name="uq_units_code"),
    )
    op.create_table(
        "suppliers",
        uuid_pk(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        active_col(),
        *timestamps(),
        sa.UniqueConstraint("code", name="uq_suppliers_code"),
    )
    op.create_table(
        "categories",
        uuid_pk(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        active_col(),
        *timestamps(),
        sa.UniqueConstraint("code", name="uq_categories_code"),
    )
    op.create_table(
        "ingredients",
        uuid_pk(),
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
        active_col(),
        *timestamps(),
        sa.ForeignKeyConstraint(["storage_unit_id"], ["units.id"]),
        sa.ForeignKeyConstraint(["purchase_unit_id"], ["units.id"]),
        sa.ForeignKeyConstraint(["default_supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["default_location_id"], ["locations.id"]),
        sa.CheckConstraint("wac >= 0", name="ck_ingredients_wac_nonneg"),
        sa.UniqueConstraint("sku", name="uq_ingredients_sku"),
        sa.UniqueConstraint("barcode", name="uq_ingredients_barcode"),
    )
    op.create_index("ix_ingredients_storage_unit_id", "ingredients", ["storage_unit_id"])
    op.create_index("ix_ingredients_purchase_unit_id", "ingredients", ["purchase_unit_id"])

    op.create_table(
        "ingredient_unit_conversions",
        uuid_pk(),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factor", sa.Numeric(18, 6), nullable=False),
        sa.Column("notes", sa.String(255), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["from_unit_id"], ["units.id"]),
        sa.ForeignKeyConstraint(["to_unit_id"], ["units.id"]),
        sa.CheckConstraint("factor > 0", name="ck_ing_conv_factor_positive"),
        sa.UniqueConstraint("ingredient_id", "from_unit_id", "to_unit_id", name="uq_ingredient_unit_conv"),
    )
    op.create_index("ix_ingredient_unit_conversions_ingredient_id", "ingredient_unit_conversions", ["ingredient_id"])
    op.create_index("ix_ingredient_unit_conversions_from_unit_id", "ingredient_unit_conversions", ["from_unit_id"])
    op.create_index("ix_ingredient_unit_conversions_to_unit_id", "ingredient_unit_conversions", ["to_unit_id"])

    op.create_table(
        "products",
        uuid_pk(),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name_en", sa.String(128), nullable=False),
        sa.Column("name_ar", sa.String(128), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        active_col(),
        *timestamps(),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])

    op.create_table(
        "product_variants",
        uuid_pk(),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("barcode", sa.String(64), nullable=True),
        active_col(),
        *timestamps(),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.CheckConstraint("price >= 0", name="ck_variant_price_nonneg"),
        sa.UniqueConstraint("product_id", "sku", name="uq_variant_product_sku"),
        sa.UniqueConstraint("barcode", name="uq_product_variants_barcode"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])

    op.create_table(
        "recipe_versions",
        uuid_pk(),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.UniqueConstraint("variant_id", "version_number", name="uq_recipe_variant_version"),
    )
    op.create_index("ix_recipe_versions_variant_id", "recipe_versions", ["variant_id"])

    op.create_table(
        "recipe_items",
        uuid_pk(),
        sa.Column("recipe_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["recipe_version_id"], ["recipe_versions.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
        sa.CheckConstraint("quantity > 0", name="ck_recipe_item_qty_positive"),
    )
    op.create_index("ix_recipe_items_recipe_version_id", "recipe_items", ["recipe_version_id"])
    op.create_index("ix_recipe_items_ingredient_id", "recipe_items", ["ingredient_id"])
    op.create_index("ix_recipe_items_unit_id", "recipe_items", ["unit_id"])

    op.create_table(
        "modifier_groups",
        uuid_pk(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("min_select", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_select", sa.Integer(), nullable=False, server_default="1"),
        active_col(),
        *timestamps(),
        sa.UniqueConstraint("code", name="uq_modifier_groups_code"),
    )
    op.create_table(
        "product_modifier_groups",
        uuid_pk(),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modifier_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["modifier_group_id"], ["modifier_groups.id"]),
        sa.UniqueConstraint("product_id", "modifier_group_id", name="uq_product_mod_group"),
    )
    op.create_index("ix_product_modifier_groups_product_id", "product_modifier_groups", ["product_id"])
    op.create_index("ix_product_modifier_groups_modifier_group_id", "product_modifier_groups", ["modifier_group_id"])

    op.create_table(
        "modifiers",
        uuid_pk(),
        sa.Column("modifier_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(64), nullable=False),
        sa.Column("price_delta", sa.Numeric(12, 2), nullable=False),
        active_col(),
        *timestamps(),
        sa.ForeignKeyConstraint(["modifier_group_id"], ["modifier_groups.id"]),
        sa.CheckConstraint("price_delta >= 0", name="ck_modifier_price_nonneg"),
    )
    op.create_index("ix_modifiers_modifier_group_id", "modifiers", ["modifier_group_id"])

    op.create_table(
        "modifier_effects",
        uuid_pk(),
        sa.Column("modifier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("effect_type", sa.String(16), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("replace_with_ingredient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=True),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("multiply_factor", sa.Numeric(14, 6), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["modifier_id"], ["modifiers.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["replace_with_ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
        sa.CheckConstraint(
            "effect_type IN ('ADD', 'REMOVE', 'REPLACE', 'MULTIPLY')",
            name="ck_modifier_effect_type",
        ),
    )
    op.create_index("ix_modifier_effects_modifier_id", "modifier_effects", ["modifier_id"])
    op.create_index("ix_modifier_effects_ingredient_id", "modifier_effects", ["ingredient_id"])
    op.create_index("ix_modifier_effects_replace_with_ingredient_id", "modifier_effects", ["replace_with_ingredient_id"])
    op.create_index("ix_modifier_effects_unit_id", "modifier_effects", ["unit_id"])


def _create_inventory_tables() -> None:
    op.create_table(
        "purchase_orders",
        uuid_pk(),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ORDERED', 'PARTIALLY_RECEIVED', 'RECEIVED', 'CANCELLED')",
            name="ck_purchase_orders_status",
        ),
    )
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_branch_id", "purchase_orders", ["branch_id"])

    op.create_table(
        "purchase_order_items",
        uuid_pk(),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordered_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 6), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.CheckConstraint("ordered_qty > 0", name="ck_purchase_order_items_qty_positive"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_purchase_order_items_cost_nonneg"),
    )
    op.create_index("ix_purchase_order_items_purchase_order_id", "purchase_order_items", ["purchase_order_id"])
    op.create_index("ix_purchase_order_items_ingredient_id", "purchase_order_items", ["ingredient_id"])

    op.create_table(
        "goods_receipts",
        uuid_pk(),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("received_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["received_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["confirmed_by_id"], ["users.id"]),
        sa.CheckConstraint("status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')", name="ck_goods_receipts_status"),
    )
    op.create_index("ix_goods_receipts_purchase_order_id", "goods_receipts", ["purchase_order_id"])
    op.create_index("ix_goods_receipts_supplier_id", "goods_receipts", ["supplier_id"])
    op.create_index("ix_goods_receipts_location_id", "goods_receipts", ["location_id"])
    op.create_index("ix_goods_receipts_branch_id", "goods_receipts", ["branch_id"])

    op.create_table(
        "goods_receipt_items",
        uuid_pk(),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 6), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["receipt_id"], ["goods_receipts.id"]),
        sa.ForeignKeyConstraint(["purchase_order_item_id"], ["purchase_order_items.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.CheckConstraint("received_qty > 0", name="ck_goods_receipt_items_qty_positive"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_goods_receipt_items_cost_nonneg"),
    )
    op.create_index("ix_goods_receipt_items_receipt_id", "goods_receipt_items", ["receipt_id"])
    op.create_index("ix_goods_receipt_items_purchase_order_item_id", "goods_receipt_items", ["purchase_order_item_id"])
    op.create_index("ix_goods_receipt_items_ingredient_id", "goods_receipt_items", ["ingredient_id"])

    op.create_table(
        "inventory_balances",
        uuid_pk(),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qty_on_hand", sa.Numeric(14, 3), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.UniqueConstraint("ingredient_id", "location_id", name="uq_inventory_balance_item_location"),
    )
    op.create_index("ix_inventory_balances_ingredient_id", "inventory_balances", ["ingredient_id"])
    op.create_index("ix_inventory_balances_location_id", "inventory_balances", ["location_id"])
    op.create_index("ix_inventory_balances_branch_id", "inventory_balances", ["branch_id"])

    op.create_table(
        "inventory_batches",
        uuid_pk(),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("remaining_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("receipt_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["receipt_line_id"], ["goods_receipt_items.id"]),
        sa.CheckConstraint("received_qty >= 0", name="ck_inventory_batches_received_nonneg"),
        sa.CheckConstraint("remaining_qty >= 0", name="ck_inventory_batches_remaining_nonneg"),
    )
    op.create_index("ix_inventory_batches_ingredient_id", "inventory_batches", ["ingredient_id"])
    op.create_index("ix_inventory_batches_location_id", "inventory_batches", ["location_id"])
    op.create_index("ix_inventory_batches_branch_id", "inventory_batches", ["branch_id"])
    op.create_index("ix_inventory_batches_receipt_line_id", "inventory_batches", ["receipt_line_id"])

    op.create_table(
        "stock_movements",
        uuid_pk(),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_base", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 6), nullable=True),
        sa.Column("reference_type", sa.String(64), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.CheckConstraint("quantity_base <> 0", name="ck_stock_movements_qty_nonzero"),
        sa.CheckConstraint(
            "type IN ('PURCHASE_RECEIPT', 'SALE', 'SALE_REVERSAL', 'WASTE', "
            "'INTERNAL_USE', 'ADJUSTMENT', 'COUNT_VARIANCE', 'RETURN_TO_STOCK', "
            "'TRANSFER_IN', 'TRANSFER_OUT')",
            name="ck_stock_movements_type",
        ),
    )
    op.create_index("ix_stock_movements_type", "stock_movements", ["type"])
    op.create_index("ix_stock_movements_ingredient_id", "stock_movements", ["ingredient_id"])
    op.create_index("ix_stock_movements_location_id", "stock_movements", ["location_id"])
    op.create_index("ix_stock_movements_branch_id", "stock_movements", ["branch_id"])
    op.create_index("ix_stock_movements_reference_type", "stock_movements", ["reference_type"])
    op.create_index("ix_stock_movements_reference_id", "stock_movements", ["reference_id"])
    op.create_index("ix_stock_movements_user_id", "stock_movements", ["user_id"])

    op.create_table(
        "waste_records",
        uuid_pk(),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_base", sa.Numeric(14, 3), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("movement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["movement_id"], ["stock_movements.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.CheckConstraint("quantity_base > 0", name="ck_waste_records_qty_positive"),
    )
    op.create_index("ix_waste_records_ingredient_id", "waste_records", ["ingredient_id"])
    op.create_index("ix_waste_records_location_id", "waste_records", ["location_id"])
    op.create_index("ix_waste_records_branch_id", "waste_records", ["branch_id"])

    op.create_table(
        "stock_counts",
        uuid_pk(),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("counted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("posted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["counted_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["posted_by_id"], ["users.id"]),
        sa.CheckConstraint("status IN ('DRAFT', 'POSTED', 'CANCELLED')", name="ck_stock_counts_status"),
    )
    op.create_index("ix_stock_counts_location_id", "stock_counts", ["location_id"])
    op.create_index("ix_stock_counts_branch_id", "stock_counts", ["branch_id"])

    op.create_table(
        "stock_count_items",
        uuid_pk(),
        sa.Column("stock_count_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theoretical_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("actual_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("variance_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("movement_id", postgresql.UUID(as_uuid=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["stock_count_id"], ["stock_counts.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["movement_id"], ["stock_movements.id"]),
        sa.CheckConstraint("theoretical_qty >= 0", name="ck_stock_count_items_theoretical_nonneg"),
        sa.CheckConstraint("actual_qty >= 0", name="ck_stock_count_items_actual_nonneg"),
        sa.UniqueConstraint("stock_count_id", "ingredient_id", name="uq_stock_count_item_ingredient"),
    )
    op.create_index("ix_stock_count_items_stock_count_id", "stock_count_items", ["stock_count_id"])
    op.create_index("ix_stock_count_items_ingredient_id", "stock_count_items", ["ingredient_id"])

    op.create_table(
        "supplier_ingredient_prices",
        uuid_pk(),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price", sa.Numeric(14, 6), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
        sa.CheckConstraint("price >= 0", name="ck_supplier_ingredient_prices_price_nonneg"),
        sa.UniqueConstraint(
            "supplier_id",
            "ingredient_id",
            "unit_id",
            "effective_from",
            name="uq_supplier_ingredient_price_effective",
        ),
    )
    op.create_index("ix_supplier_ingredient_prices_supplier_id", "supplier_ingredient_prices", ["supplier_id"])
    op.create_index("ix_supplier_ingredient_prices_ingredient_id", "supplier_ingredient_prices", ["ingredient_id"])
    op.create_index("ix_supplier_ingredient_prices_unit_id", "supplier_ingredient_prices", ["unit_id"])

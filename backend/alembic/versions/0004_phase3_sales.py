"""phase3 pos and orders

Revision ID: 0004_phase3_sales
Revises: 0003_phase2_inventory
Create Date: 2026-10-15

"""

# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase3_sales"
down_revision: str | None = "0003_phase2_inventory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_pk() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    _create_sales_tables()


def downgrade() -> None:
    for table_name in [
        "idempotency_keys",
        "sale_item_consumptions",
        "sale_item_modifiers",
        "payments",
        "sale_items",
        "sales",
    ]:
        op.drop_table(table_name)


def _create_sales_tables() -> None:
    op.create_table(
        "sales",
        uuid_pk(),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("order_type", sa.String(16), nullable=False, server_default="dine_in"),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("cogs_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("flagged_negative_stock", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *timestamps(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.CheckConstraint("status IN ('DRAFT', 'CONFIRMED', 'PREPARING', 'COMPLETED', 'CANCELLED')", name="ck_sales_status"),
        sa.CheckConstraint("order_type IN ('dine_in', 'takeaway')", name="ck_sales_order_type"),
        sa.CheckConstraint("subtotal >= 0", name="ck_sales_subtotal_nonneg"),
        sa.CheckConstraint("discount >= 0", name="ck_sales_discount_nonneg"),
        sa.CheckConstraint("tax >= 0", name="ck_sales_tax_nonneg"),
        sa.CheckConstraint("total >= 0", name="ck_sales_total_nonneg"),
        sa.CheckConstraint("cogs_total >= 0", name="ck_sales_cogs_nonneg"),
    )
    op.create_index("ix_sales_branch_id", "sales", ["branch_id"])
    op.create_index("ix_sales_user_id", "sales", ["user_id"])

    op.create_table(
        "sale_items",
        uuid_pk(),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cogs", sa.Numeric(12, 2), nullable=False, server_default="0"),
        *timestamps(),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.ForeignKeyConstraint(["recipe_version_id"], ["recipe_versions.id"]),
        sa.CheckConstraint("qty > 0", name="ck_sale_items_qty_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_sale_items_price_nonneg"),
        sa.CheckConstraint("line_total >= 0", name="ck_sale_items_line_total_nonneg"),
        sa.CheckConstraint("cogs >= 0", name="ck_sale_items_cogs_nonneg"),
    )
    op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"])
    op.create_index("ix_sale_items_variant_id", "sale_items", ["variant_id"])

    op.create_table(
        "sale_item_modifiers",
        uuid_pk(),
        sa.Column("sale_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modifier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price_delta", sa.Numeric(12, 2), nullable=False, server_default="0"),
        *timestamps(),
        sa.ForeignKeyConstraint(["sale_item_id"], ["sale_items.id"]),
        sa.ForeignKeyConstraint(["modifier_id"], ["modifiers.id"]),
    )
    op.create_index("ix_sale_item_modifiers_sale_item_id", "sale_item_modifiers", ["sale_item_id"])
    op.create_index("ix_sale_item_modifiers_modifier_id", "sale_item_modifiers", ["modifier_id"])

    op.create_table(
        "sale_item_consumptions",
        uuid_pk(),
        sa.Column("sale_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qty_base", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 6), nullable=False),
        sa.Column("line_cogs", sa.Numeric(12, 2), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["sale_item_id"], ["sale_items.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.CheckConstraint("qty_base > 0", name="ck_sale_item_cons_qty_positive"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_sale_item_cons_cost_nonneg"),
        sa.CheckConstraint("line_cogs >= 0", name="ck_sale_item_cons_cogs_nonneg"),
    )
    op.create_index("ix_sale_item_consumptions_sale_item_id", "sale_item_consumptions", ["sale_item_id"])
    op.create_index("ix_sale_item_consumptions_ingredient_id", "sale_item_consumptions", ["ingredient_id"])

    op.create_table(
        "payments",
        uuid_pk(),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"]),
        sa.CheckConstraint("method IN ('CASH', 'CARD', 'WALLET')", name="ck_payments_method"),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )
    op.create_index("ix_payments_sale_id", "payments", ["sale_id"])

    op.create_table(
        "idempotency_keys",
        uuid_pk(),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("key", name="uq_idempotency_keys_key"),
    )

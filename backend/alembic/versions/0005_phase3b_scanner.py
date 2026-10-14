"""phase3b phone scanner

Revision ID: 0005_phase3b_scanner
Revises: 0004_phase3_sales
Create Date: 2026-10-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase3b_scanner"
down_revision: str | None = "0004_phase3_sales"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scanner_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PAIRING"),
        sa.Column("pairing_token_hash", sa.String(64), nullable=True),
        sa.Column("pairing_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_token_hash", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.CheckConstraint(
            "mode IN ('CASHIER', 'RECEIVE', 'COUNT', 'WASTE')",
            name="ck_scanner_sessions_mode",
        ),
        sa.CheckConstraint(
            "status IN ('PAIRING', 'PAIRED', 'EXPIRED', 'REVOKED')",
            name="ck_scanner_sessions_status",
        ),
        sa.CheckConstraint(
            "expires_at <= created_at + interval '12 hours'",
            name="ck_scanner_sessions_max_12h",
        ),
        sa.UniqueConstraint("pairing_token_hash", name="uq_scanner_sessions_pairing_token_hash"),
        sa.UniqueConstraint("device_token_hash", name="uq_scanner_sessions_device_token_hash"),
    )
    op.create_index("ix_scanner_sessions_station_id", "scanner_sessions", ["station_id"])
    op.create_index("ix_scanner_sessions_user_id", "scanner_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_scanner_sessions_user_id", table_name="scanner_sessions")
    op.drop_index("ix_scanner_sessions_station_id", table_name="scanner_sessions")
    op.drop_table("scanner_sessions")

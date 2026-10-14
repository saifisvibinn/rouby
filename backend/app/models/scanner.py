from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import UUIDPrimaryKeyMixin


class ScannerSession(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "scanner_sessions"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('CASHIER', 'RECEIVE', 'COUNT', 'WASTE')",
            name="ck_scanner_sessions_mode",
        ),
        CheckConstraint(
            "status IN ('PAIRING', 'PAIRED', 'EXPIRED', 'REVOKED')",
            name="ck_scanner_sessions_status",
        ),
        CheckConstraint(
            "expires_at <= created_at + interval '12 hours'",
            name="ck_scanner_sessions_max_12h",
        ),
    )

    station_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PAIRING")
    pairing_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    pairing_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User")

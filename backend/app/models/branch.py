from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import SoftActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Branch(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "branches"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(128), nullable=False)

    locations: Mapped[list[Location]] = relationship(back_populates="branch")


class Location(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftActiveMixin):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("branch_id", "code", name="uq_locations_branch_code"),)

    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branches.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(128), nullable=False)

    branch: Mapped[Branch] = relationship(back_populates="locations")

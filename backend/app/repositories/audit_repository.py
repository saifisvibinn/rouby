from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        user_id: UUID | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
        notes: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            before=before,
            after=after,
            ip_address=ip_address,
            request_id=request_id,
            notes=notes,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

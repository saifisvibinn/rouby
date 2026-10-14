from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditRepository(session)

    async def write(
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
    ) -> None:
        await self._repo.create(
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

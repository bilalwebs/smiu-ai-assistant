"""``audit_logs`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §24).

Append-only security and compliance trail. Rows are never edited by
application code.
"""

from __future__ import annotations

import uuid

from app.models import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Data access for :class:`app.models.audit_logs.AuditLog`."""

    model = AuditLog

    async def list_by_actor(
        self,
        actor_user_id: uuid.UUID,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AuditLog]:
        """List an actor's audit trail, newest first."""
        return await self.list(
            AuditLog.actor_user_id == actor_user_id,
            order_by=[AuditLog.created_at.desc()],
            limit=limit,
            offset=offset,
        )

    async def list_by_resource(
        self,
        resource_type: str,
        resource_id: str | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AuditLog]:
        """List audit events for a resource, newest first."""
        filters = [AuditLog.resource_type == resource_type]
        if resource_id is not None:
            filters.append(AuditLog.resource_id == resource_id)
        return await self.list(
            *filters,
            order_by=[AuditLog.created_at.desc()],
            limit=limit,
            offset=offset,
        )


__all__ = ["AuditLogRepository"]

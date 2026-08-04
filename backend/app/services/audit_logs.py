"""``audit_logs`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §24).

Append-only security and compliance trail for privileged actions, destructive
operations, auth events, and knowledge base changes. Rows are never edited, so
the service exposes creation and reads only (DATABASE_DESIGN.md §24.2).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog
from app.repositories import AuditLogRepository, Page, UserRepository
from app.services.base import BaseService
from app.services.exceptions import NotFoundError, ValidationError


class AuditLogService(BaseService):
    """Append-only audit operations for :class:`app.models.audit_logs.AuditLog`."""

    def __init__(
        self,
        session: AsyncSession,
        logs: AuditLogRepository | None = None,
        users: UserRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._logs = logs or AuditLogRepository(session)
        self._users = users or UserRepository(session)

    async def create_log(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor_user_id: uuid.UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
    ) -> AuditLog:
        """Record one immutable audit event (DATABASE_DESIGN.md §24)."""
        action = self._validate_not_blank(action, field="action")
        resource_type = self._validate_not_blank(resource_type, field="resource_type")
        if len(action) > 100:
            raise ValidationError(
                message="action must be at most 100 characters",
                details=[{"field": "action", "reason": "too long"}],
            )
        if len(resource_type) > 100:
            raise ValidationError(
                message="resource_type must be at most 100 characters",
                details=[{"field": "resource_type", "reason": "too long"}],
            )
        if resource_id is not None and len(resource_id) > 100:
            raise ValidationError(
                message="resource_id must be at most 100 characters",
                details=[{"field": "resource_id", "reason": "too long"}],
            )
        if correlation_id is not None and len(correlation_id) > 100:
            raise ValidationError(
                message="correlation_id must be at most 100 characters",
                details=[{"field": "correlation_id", "reason": "too long"}],
            )
        if (
            actor_user_id is not None
            and await self._users.get_by_id(actor_user_id) is None
        ):
            raise NotFoundError(message="Actor user not found")
        return await self._logs.create(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor_user_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )

    async def list_by_actor(
        self,
        *,
        actor_user_id: uuid.UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AuditLog]:
        """List an actor's audit trail, newest first."""
        if await self._users.get_by_id(actor_user_id) is None:
            raise NotFoundError(message="Actor user not found")
        return await self._logs.list_by_actor(
            actor_user_id, limit=limit, offset=offset
        )

    async def list_by_resource(
        self,
        *,
        resource_type: str,
        resource_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AuditLog]:
        """List audit events for a resource, newest first."""
        resource_type = self._validate_not_blank(resource_type, field="resource_type")
        return await self._logs.list_by_resource(
            resource_type, resource_id, limit=limit, offset=offset
        )

    async def list_logs(
        self, *, page: int = 1, limit: int = 20
    ) -> Page[AuditLog]:
        """Paginate the full audit trail, newest first (admin-only, §25)."""
        return await self._logs.paginate(
            page=page,
            limit=limit,
            order_by=[AuditLog.created_at.desc()],
        )

"""Audit log schemas (API_SPECIFICATION.md §25; DATABASE_DESIGN.md §24).

Purpose:
    Read-only view of the append-only audit trail for admin endpoints. Values
    never expose actor session/credential details.
"""

from __future__ import annotations

import uuid

from app.schemas.base import ApiModel, UtcDateTime


class AuditLogRead(ApiModel):
    """One append-only audit event for ``GET /admin/audit-logs``."""

    id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    correlation_id: str | None = None
    created_at: UtcDateTime


__all__ = ["AuditLogRead"]

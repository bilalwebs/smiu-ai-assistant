"""Session schemas (API_SPECIFICATION.md §17; DATABASE_DESIGN.md §25).

Purpose:
    Define the active-session payloads a user can list and revoke. Refresh-token
    digests are never serialized.
"""

from __future__ import annotations

import uuid

from app.schemas.base import ApiModel, UtcDateTime


class SessionRead(ApiModel):
    """Active session summary for ``GET /users/me/sessions`` (§17)."""

    id: uuid.UUID
    device_name: str | None = None
    ip_address: str | None = None
    created_at: UtcDateTime
    last_used_at: UtcDateTime | None = None
    expires_at: UtcDateTime


__all__ = ["SessionRead"]

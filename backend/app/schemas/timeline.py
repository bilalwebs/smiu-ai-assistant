"""Request timeline schemas (API_SPECIFICATION.md §18; DATABASE_DESIGN.md §18).

Purpose:
    Define the read representation of the append-only status-transition log.
"""

from __future__ import annotations

import uuid

from app.models import RequestStatus
from app.schemas.base import ApiModel, UtcDateTime


class TimelineEventRead(ApiModel):
    """One append-only status-transition event (DATABASE_DESIGN.md §18)."""

    id: uuid.UUID
    request_id: uuid.UUID
    from_status: RequestStatus | None = None
    to_status: RequestStatus
    action: str
    note: str | None = None
    actor_user_id: uuid.UUID | None = None
    created_at: UtcDateTime

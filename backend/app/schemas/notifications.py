"""Notification schemas (API_SPECIFICATION.md §19).

Purpose:
    Define the user-facing activity-feed payloads. Notifications are generated
    by workflow events, never ad hoc (BACKEND_ARCHITECTURE.md §32.5).
"""

from __future__ import annotations

import uuid

from app.models import NotificationPriority, NotificationType
from app.schemas.base import ApiModel, UtcDateTime


class NotificationRead(ApiModel):
    """User-facing activity notification (DATABASE_DESIGN.md §19)."""

    id: uuid.UUID
    user_id: uuid.UUID
    request_id: uuid.UUID | None = None
    type: NotificationType
    priority: NotificationPriority
    title: str
    body: str | None = None
    link: str | None = None
    icon: str | None = None
    read_at: UtcDateTime | None = None
    delivered_at: UtcDateTime | None = None
    created_at: UtcDateTime


class UnreadCountRead(ApiModel):
    """Unread notification count for a user."""

    unread: int

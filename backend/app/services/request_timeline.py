"""``request_timeline`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §18).

Workflow & Support: append-only status-transition history. Rows are never
updated or deleted by application code, so the service exposes only event
creation and reads (DATABASE_DESIGN.md §18; BACKEND_ARCHITECTURE.md §32.6).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RequestStatus, RequestTimeline
from app.repositories import RequestRepository, RequestTimelineRepository, UserRepository
from app.services.base import BaseService
from app.services.exceptions import NotFoundError


class RequestTimelineService(BaseService):
    """Append-only timeline operations for
    :class:`app.models.request_timeline.RequestTimeline`.
    """

    def __init__(
        self,
        session: AsyncSession,
        timeline: RequestTimelineRepository | None = None,
        requests: RequestRepository | None = None,
        users: UserRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._timeline = timeline or RequestTimelineRepository(session)
        self._requests = requests or RequestRepository(session)
        self._users = users or UserRepository(session)

    async def add_event(
        self,
        *,
        request_id: uuid.UUID,
        to_status: RequestStatus,
        action: str,
        from_status: RequestStatus | None = None,
        note: str | None = None,
        actor_user_id: uuid.UUID | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> RequestTimeline:
        """Record one status-transition event on a request."""
        if await self._requests.get_by_id(request_id) is None:
            raise NotFoundError(message="Request not found")
        if (
            actor_user_id is not None
            and await self._users.get_by_id(actor_user_id) is None
        ):
            raise NotFoundError(message="Actor user not found")
        to_status = self._validate_enum(to_status, RequestStatus, field="to_status")
        if from_status is not None:
            from_status = self._validate_enum(
                from_status, RequestStatus, field="from_status"
            )
        action = self._validate_not_blank(action, field="action")
        values: dict[str, Any] = {
            "request_id": request_id,
            "from_status": from_status,
            "to_status": to_status,
            "action": action,
            "note": note,
            "actor_user_id": actor_user_id,
        }
        if metadata_ is not None:
            values["metadata_"] = metadata_
        return await self._timeline.create(**values)

    async def get_events(
        self,
        *,
        request_id: uuid.UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[RequestTimeline]:
        """Return a request's timeline events in chronological order."""
        if await self._requests.get_by_id(request_id) is None:
            raise NotFoundError(message="Request not found")
        return await self._timeline.list_by_request(
            request_id, limit=limit, offset=offset
        )

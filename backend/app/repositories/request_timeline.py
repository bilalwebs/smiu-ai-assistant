"""``request_timeline`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §18).

Workflow & Support: append-only status-transition history driving the timeline
UI. Rows are never updated or deleted by application code.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.sql.base import ExecutableOption

from app.models import RequestTimeline
from app.repositories.base import BaseRepository


class RequestTimelineRepository(BaseRepository[RequestTimeline]):
    """Data access for :class:`app.models.request_timeline.RequestTimeline`."""

    model = RequestTimeline

    async def list_by_request(
        self,
        request_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[RequestTimeline]:
        """List a request's timeline events in chronological order."""
        return await self.list(
            RequestTimeline.request_id == request_id,
            order_by=[RequestTimeline.created_at.asc()],
            options=options,
            limit=limit,
            offset=offset,
        )


__all__ = ["RequestTimelineRepository"]

"""``requests`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §17).

Workflow & Support: the core persistable unit of student workflow automation —
pending work, per-status listings, and per-owner/per-department pagination.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.sql.base import ExecutableOption

from app.models import Request, RequestStatus
from app.repositories.base import BaseRepository, Page

_ACTIVE_STATUSES: tuple[RequestStatus, ...] = (
    RequestStatus.SUBMITTED,
    RequestStatus.IN_REVIEW,
    RequestStatus.ASSIGNED,
    RequestStatus.PROCESSING,
)


class RequestRepository(BaseRepository[Request]):
    """Data access for :class:`app.models.requests.Request`."""

    model = Request

    async def get_by_request_no(
        self, request_no: str, *, options: Sequence[ExecutableOption] = ()
    ) -> Request | None:
        """Fetch a live request by its unique request number."""
        return await self.get(Request.request_no == request_no, options=options)

    async def get_pending(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> list[Request]:
        """List live in-flight requests, oldest first (queue order)."""
        return await self.list(
            Request.status.in_(_ACTIVE_STATUSES),
            order_by=[Request.created_at.asc()],
            limit=limit,
            offset=offset,
        )

    async def get_by_status(
        self,
        status: RequestStatus,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Request]:
        """List live requests in a given status, newest first."""
        return await self.list(
            Request.status == status,
            order_by=[Request.created_at.desc()],
            limit=limit,
            offset=offset,
        )

    async def get_student_requests(
        self, user_id: uuid.UUID, *, page: int = 1, limit: int = 20
    ) -> Page[Request]:
        """Paginate a student's requests, newest first."""
        return await self.paginate(
            page=page,
            limit=limit,
            filters=[Request.user_id == user_id],
            order_by=[Request.created_at.desc()],
        )

    async def get_department_requests(
        self, department_id: uuid.UUID, *, page: int = 1, limit: int = 20
    ) -> Page[Request]:
        """Paginate a department's requests, newest first."""
        return await self.paginate(
            page=page,
            limit=limit,
            filters=[Request.department_id == department_id],
            order_by=[Request.created_at.desc()],
        )


__all__ = ["RequestRepository"]

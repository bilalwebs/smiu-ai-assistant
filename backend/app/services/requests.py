"""``requests`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §17).

Workflow & Support: request creation and guarded lifecycle/status transitions.
Terminal states (``resolved``, ``closed``, ``rejected``) are absorbing;
transitions are validated against an explicit state machine before any write.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Request,
    RequestPriority,
    RequestSource,
    RequestStatus,
    RequestType,
)
from app.repositories import DepartmentRepository, RequestRepository, UserRepository
from app.services.base import BaseService
from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from app.utils.time import utc_now

_INITIAL_STATUSES: frozenset[RequestStatus] = frozenset(
    {RequestStatus.DRAFT, RequestStatus.SUBMITTED}
)

_ALLOWED_TRANSITIONS: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.DRAFT: frozenset({RequestStatus.SUBMITTED, RequestStatus.IN_REVIEW}),
    RequestStatus.SUBMITTED: frozenset(
        {
            RequestStatus.IN_REVIEW,
            RequestStatus.ASSIGNED,
            RequestStatus.PROCESSING,
            RequestStatus.RESOLVED,
            RequestStatus.REJECTED,
        }
    ),
    RequestStatus.IN_REVIEW: frozenset(
        {
            RequestStatus.ASSIGNED,
            RequestStatus.PROCESSING,
            RequestStatus.RESOLVED,
            RequestStatus.REJECTED,
        }
    ),
    RequestStatus.ASSIGNED: frozenset(
        {
            RequestStatus.ASSIGNED,
            RequestStatus.PROCESSING,
            RequestStatus.RESOLVED,
            RequestStatus.REJECTED,
        }
    ),
    RequestStatus.PROCESSING: frozenset(
        {RequestStatus.RESOLVED, RequestStatus.REJECTED}
    ),
    RequestStatus.RESOLVED: frozenset({RequestStatus.CLOSED}),
    RequestStatus.CLOSED: frozenset(),
    RequestStatus.REJECTED: frozenset(),
}


class RequestService(BaseService):
    """Lifecycle operations for :class:`app.models.requests.Request`."""

    def __init__(
        self,
        session: AsyncSession,
        requests: RequestRepository | None = None,
        users: UserRepository | None = None,
        departments: DepartmentRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._requests = requests or RequestRepository(session)
        self._users = users or UserRepository(session)
        self._departments = departments or DepartmentRepository(session)

    async def create_request(
        self,
        *,
        user_id: uuid.UUID,
        request_type: RequestType,
        title: str,
        status: RequestStatus = RequestStatus.DRAFT,
        category: str | None = None,
        department_id: uuid.UUID | None = None,
        description: str | None = None,
        priority: RequestPriority = RequestPriority.MEDIUM,
        source: RequestSource = RequestSource.MANUAL,
        request_no: str | None = None,
    ) -> Request:
        """Create a request in an initial state (draft or submitted)."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        if department_id is not None:
            department = await self._departments.get_by_id(department_id)
            if department is None:
                raise NotFoundError(message="Department not found")
        request_type = self._validate_enum(request_type, RequestType, field="request_type")
        status = self._validate_enum(status, RequestStatus, field="status")
        if status not in _INITIAL_STATUSES:
            raise ValidationError(
                message="Requests can only be created in an initial state",
                details=[{"field": "status", "reason": "not an initial state"}],
            )
        title = self._validate_not_blank(title, field="title")
        request_no = await self._allocate_request_no(request_no)
        return await self._requests.create(
            request_no=request_no,
            user_id=user_id,
            department_id=department_id,
            request_type=request_type,
            category=category,
            priority=priority,
            status=status,
            title=title,
            description=description,
            source=source,
        )

    async def assign_request(
        self, *, request_id: uuid.UUID, assigned_to: uuid.UUID
    ) -> Request:
        """Assign an in-flight request to a staff member."""
        request = await self._require_request(request_id)
        if await self._users.get_by_id(assigned_to) is None:
            raise NotFoundError(message="Assignee user not found")
        self._assert_transition_allowed(request.status, RequestStatus.ASSIGNED)
        return await self._requests.update(
            request, status=RequestStatus.ASSIGNED, assigned_to=assigned_to
        )

    async def resolve_request(
        self,
        *,
        request_id: uuid.UUID,
        resolution_notes: str | None = None,
    ) -> Request:
        """Resolve an in-flight request (records ``resolved_at``)."""
        return await self.change_status(
            request_id=request_id,
            status=RequestStatus.RESOLVED,
            resolution_notes=resolution_notes,
        )

    async def reject_request(
        self, *, request_id: uuid.UUID, rejection_reason: str
    ) -> Request:
        """Reject an in-flight request with a mandatory reason."""
        return await self.change_status(
            request_id=request_id,
            status=RequestStatus.REJECTED,
            rejection_reason=rejection_reason,
        )

    async def change_status(
        self,
        *,
        request_id: uuid.UUID,
        status: RequestStatus,
        resolution_notes: str | None = None,
        rejection_reason: str | None = None,
    ) -> Request:
        """Transition a request through the documented status machine."""
        request = await self._require_request(request_id)
        status = self._validate_enum(status, RequestStatus, field="status")
        if status == request.status:
            raise InvalidStateError(
                message=f"Request is already {request.status.value}",
                details=[{"field": "status", "reason": "no state change"}],
            )
        self._assert_transition_allowed(request.status, status)
        changes: dict[str, Any] = {"status": status}
        if status == RequestStatus.RESOLVED:
            changes["resolved_at"] = utc_now()
            if resolution_notes is not None:
                changes["resolution_notes"] = resolution_notes
        elif status == RequestStatus.REJECTED:
            rejection_reason = self._validate_not_blank(
                rejection_reason, field="rejection_reason"
            )
            changes["rejected_at"] = utc_now()
            changes["rejection_reason"] = rejection_reason
        elif status == RequestStatus.CLOSED:
            changes["closed_at"] = utc_now()
        return await self._requests.update(request, **changes)

    async def _allocate_request_no(self, provided: str | None) -> str:
        """Return the provided request number or allocate a unique one."""
        if provided is not None:
            request_no = self._validate_not_blank(provided, field="request_no")
            if await self._requests.get_by_request_no(request_no) is not None:
                raise ConflictError(
                    message="A request with this number already exists",
                    details=[{"field": "request_no", "reason": "already in use"}],
                )
            return request_no
        for _ in range(5):
            candidate = f"REQ-{uuid.uuid4().hex[:8].upper()}"
            if await self._requests.get_by_request_no(candidate) is None:
                return candidate
        raise BusinessRuleError(message="Could not allocate a unique request number")

    async def _require_request(self, request_id: uuid.UUID) -> Request:
        request = await self._requests.get_by_id(request_id)
        if request is None:
            raise NotFoundError(message="Request not found")
        return request

    @staticmethod
    def _assert_transition_allowed(
        current: RequestStatus, target: RequestStatus
    ) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise InvalidStateError(
                message=f"Cannot transition request from {current.value} to {target.value}",
                details=[{"field": "status", "reason": "invalid transition"}],
            )

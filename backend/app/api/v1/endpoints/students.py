"""Student self-service endpoints (API_SPECIFICATION.md §15).

Purpose:
    Owner-scoped academic profile access for the authenticated student
    (profile + editable fields + dashboard aggregates). Every route resolves
    the acting user id from the owner-context dependency (§4.2).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.services import (
    get_notification_repository,
    get_request_repository,
    get_student_repository,
)
from app.models import Request as RequestModel
from app.models import RequestStatus
from app.repositories import NotificationRepository, RequestRepository, StudentRepository
from app.schemas.response import SuccessResponse
from app.schemas.students import StudentDashboardRead, StudentRead, StudentUpdate
from app.services.exceptions import NotFoundError
from app.utils.response import success_response

router = APIRouter(prefix="/students", tags=["students"])

_ACTIVE_STATUSES = (
    RequestStatus.SUBMITTED,
    RequestStatus.IN_REVIEW,
    RequestStatus.ASSIGNED,
    RequestStatus.PROCESSING,
)
_TERMINAL_STATUSES = (RequestStatus.RESOLVED, RequestStatus.CLOSED)


@router.get(
    "/me",
    response_model=SuccessResponse[StudentRead],
    summary="Fetch the current student profile",
)
async def get_me(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    students: StudentRepository = Depends(get_student_repository),
) -> SuccessResponse[StudentRead]:
    """Return the authenticated student's academic profile (§15)."""
    student = await students.get_by_user_id(current_user.user_id)
    if student is None:
        raise NotFoundError(message="Student profile not found")
    return success_response(request, StudentRead.model_validate(student))


@router.patch(
    "/me",
    response_model=SuccessResponse[StudentRead],
    summary="Update editable academic profile fields",
)
async def update_me(
    payload: StudentUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    students: StudentRepository = Depends(get_student_repository),
) -> SuccessResponse[StudentRead]:
    """Update the authenticated student's editable academic fields (§15)."""
    student = await students.get_by_user_id(current_user.user_id)
    if student is None:
        raise NotFoundError(message="Student profile not found")
    student = await students.update(
        student, **payload.model_dump(exclude_unset=True)
    )
    return success_response(request, StudentRead.model_validate(student))


@router.get(
    "/me/dashboard",
    response_model=SuccessResponse[StudentDashboardRead],
    summary="Dashboard aggregates for the current student",
)
async def get_dashboard(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    requests: RequestRepository = Depends(get_request_repository),
    notifications: NotificationRepository = Depends(get_notification_repository),
) -> SuccessResponse[StudentDashboardRead]:
    """Return owner-scoped dashboard counts (§15)."""
    user_id = current_user.user_id
    dashboard = StudentDashboardRead(
        active_requests=await requests.count(
            RequestModel.user_id == user_id, RequestModel.status.in_(_ACTIVE_STATUSES)
        ),
        pending_requests=await requests.count(
            RequestModel.user_id == user_id, RequestModel.status == RequestStatus.DRAFT
        ),
        resolved_requests=await requests.count(
            RequestModel.user_id == user_id, RequestModel.status.in_(_TERMINAL_STATUSES)
        ),
        unread_notifications=await notifications.count_unread(user_id),
    )
    return success_response(request, dashboard)

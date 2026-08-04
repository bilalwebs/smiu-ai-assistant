"""Workflow request endpoints (API_SPECIFICATION.md §18).

Purpose:
    Owner-scoped request lifecycle: creation, listing, detail, updates,
    status transitions, and the append-only timeline. Every route resolves the
    acting user id from the owner-context dependency and enforces ownership on
    the request it touches (§4.2).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.services import (
    get_request_repository,
    get_request_service,
    get_request_timeline_service,
)
from app.exceptions.app_error import ForbiddenError
from app.models import Request as RequestModel
from app.models import RequestStatus
from app.repositories import RequestRepository
from app.schemas.requests import (
    RequestCreate,
    RequestRead,
    RequestStatusUpdate,
    RequestUpdate,
)
from app.schemas.response import SuccessResponse
from app.schemas.timeline import TimelineEventRead
from app.services import RequestService, RequestTimelineService
from app.services.exceptions import NotFoundError
from app.utils.response import pagination_meta, success_response

router = APIRouter(prefix="/requests", tags=["requests"])


async def _require_owned_request(
    request_id: uuid.UUID,
    user_id: uuid.UUID,
    requests: RequestRepository,
) -> RequestModel:
    """Fetch a request and assert the acting user owns it."""
    request = await requests.get_by_id(request_id)
    if request is None:
        raise NotFoundError(message="Request not found")
    if request.user_id != user_id:
        raise ForbiddenError(message="You do not own this request")
    return request


@router.get(
    "",
    response_model=SuccessResponse[list[RequestRead]],
    summary="List own requests",
)
async def list_requests(
    request: Request,
    page: int = 1,
    limit: int = 20,
    request_status: RequestStatus | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    requests: RequestRepository = Depends(get_request_repository),
) -> SuccessResponse[list[RequestRead]]:
    """Paginate the acting user's requests, optionally filtered by status (§18)."""
    filters = [RequestModel.user_id == current_user.user_id]
    if request_status is not None:
        filters.append(RequestModel.status == request_status)
    page_result = await requests.paginate(
        page=page,
        limit=limit,
        filters=filters,
        order_by=[RequestModel.created_at.desc()],
    )
    return success_response(
        request,
        [RequestRead.model_validate(item) for item in page_result.items],
        pagination=pagination_meta(page_result),
    )


@router.post(
    "",
    response_model=SuccessResponse[RequestRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a request (draft or submitted)",
)
async def create_request(
    payload: RequestCreate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
) -> SuccessResponse[RequestRead]:
    """Create a request owned by the acting user (§18)."""
    created = await service.create_request(
        user_id=current_user.user_id, **payload.model_dump()
    )
    return success_response(request, RequestRead.model_validate(created))


@router.get(
    "/{request_id}",
    response_model=SuccessResponse[RequestRead],
    summary="Fetch request details",
)
async def get_request(
    request_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    requests: RequestRepository = Depends(get_request_repository),
) -> SuccessResponse[RequestRead]:
    """Return a request the acting user owns (§18)."""
    entity = await _require_owned_request(
        request_id, current_user.user_id, requests
    )
    return success_response(request, RequestRead.model_validate(entity))


@router.patch(
    "/{request_id}",
    response_model=SuccessResponse[RequestRead],
    summary="Update editable request fields",
)
async def update_request(
    request_id: uuid.UUID,
    payload: RequestUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    requests: RequestRepository = Depends(get_request_repository),
) -> SuccessResponse[RequestRead]:
    """Update editable fields of an owned request (§18)."""
    entity = await _require_owned_request(
        request_id, current_user.user_id, requests
    )
    entity = await requests.update(entity, **payload.model_dump(exclude_unset=True))
    return success_response(request, RequestRead.model_validate(entity))


@router.delete(
    "/{request_id}",
    response_model=SuccessResponse[RequestRead],
    summary="Soft-delete a request",
)
async def delete_request(
    request_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    requests: RequestRepository = Depends(get_request_repository),
) -> SuccessResponse[RequestRead]:
    """Soft-delete an owned request (§18; DATABASE_DESIGN.md §26)."""
    entity = await _require_owned_request(
        request_id, current_user.user_id, requests
    )
    entity = await requests.soft_delete(entity)
    return success_response(request, RequestRead.model_validate(entity))


@router.post(
    "/{request_id}/submit",
    response_model=SuccessResponse[RequestRead],
    summary="Submit a draft request",
)
async def submit_request(
    request_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
    requests: RequestRepository = Depends(get_request_repository),
) -> SuccessResponse[RequestRead]:
    """Transition an owned draft to ``submitted`` (§18)."""
    await _require_owned_request(request_id, current_user.user_id, requests)
    entity = await service.change_status(
        request_id=request_id, status=RequestStatus.SUBMITTED
    )
    return success_response(request, RequestRead.model_validate(entity))


@router.post(
    "/{request_id}/resolve",
    response_model=SuccessResponse[RequestRead],
    summary="Resolve a request",
)
async def resolve_request(
    request_id: uuid.UUID,
    payload: RequestStatusUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
    requests: RequestRepository = Depends(get_request_repository),
) -> SuccessResponse[RequestRead]:
    """Transition an in-flight request to ``resolved`` (§18)."""
    await _require_owned_request(request_id, current_user.user_id, requests)
    entity = await service.resolve_request(
        request_id=request_id, resolution_notes=payload.resolution_notes
    )
    return success_response(request, RequestRead.model_validate(entity))


@router.post(
    "/{request_id}/close",
    response_model=SuccessResponse[RequestRead],
    summary="Close a resolved request",
)
async def close_request(
    request_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
    requests: RequestRepository = Depends(get_request_repository),
) -> SuccessResponse[RequestRead]:
    """Transition a resolved request to ``closed`` (§18)."""
    await _require_owned_request(request_id, current_user.user_id, requests)
    entity = await service.change_status(
        request_id=request_id, status=RequestStatus.CLOSED
    )
    return success_response(request, RequestRead.model_validate(entity))


@router.post(
    "/{request_id}/reject",
    response_model=SuccessResponse[RequestRead],
    summary="Reject a request",
)
async def reject_request(
    request_id: uuid.UUID,
    payload: RequestStatusUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
    requests: RequestRepository = Depends(get_request_repository),
) -> SuccessResponse[RequestRead]:
    """Transition an in-flight request to ``rejected`` with a reason (§18)."""
    await _require_owned_request(request_id, current_user.user_id, requests)
    entity = await service.reject_request(
        request_id=request_id, rejection_reason=payload.rejection_reason or ""
    )
    return success_response(request, RequestRead.model_validate(entity))


@router.get(
    "/{request_id}/timeline",
    response_model=SuccessResponse[list[TimelineEventRead]],
    summary="Fetch the request status timeline",
)
async def get_request_timeline(
    request_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: RequestTimelineService = Depends(get_request_timeline_service),
    requests: RequestRepository = Depends(get_request_repository),
) -> SuccessResponse[list[TimelineEventRead]]:
    """Return the append-only status-transition log for an owned request (§18)."""
    await _require_owned_request(request_id, current_user.user_id, requests)
    events = await service.get_events(request_id=request_id)
    return success_response(
        request, [TimelineEventRead.model_validate(event) for event in events]
    )

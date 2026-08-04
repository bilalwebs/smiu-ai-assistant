"""User self-service endpoints (API_SPECIFICATION.md §17).

Purpose:
    Owner-scoped account/profile access for the authenticated user. Every
    route resolves the acting user id from the owner-context dependency and
    only ever operates on that user's own record (§4.2).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.services import (
    get_auth_service,
    get_session_repository,
    get_session_service,
    get_user_repository,
    get_user_service,
)
from app.exceptions.app_error import ForbiddenError
from app.models import UserSession
from app.repositories import SessionRepository, UserRepository
from app.schemas.auth import ChangePasswordRequest
from app.schemas.response import SuccessResponse
from app.schemas.sessions import SessionRead
from app.schemas.users import UserRead, UserUpdate
from app.services import AuthService, SessionService, UserService
from app.services.exceptions import NotFoundError
from app.utils.response import pagination_meta, success_response

router = APIRouter(prefix="/users", tags=["users"])


async def _require_owned_session(
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    sessions: SessionRepository,
) -> UserSession:
    """Fetch a session and assert the acting user owns it."""
    session = await sessions.get_by_id(session_id)
    if session is None:
        raise NotFoundError(message="Session not found")
    if session.user_id != user_id:
        raise ForbiddenError(message="You do not own this session")
    return session


def _request_metadata(request: Request) -> tuple[str | None, str | None]:
    """Return ``(ip_address, user_agent)`` for audit attribution."""
    ip_address = request.client.host if request.client is not None else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


@router.get(
    "/me",
    response_model=SuccessResponse[UserRead],
    summary="Fetch the authenticated user profile",
)
async def get_me(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    users: UserRepository = Depends(get_user_repository),
) -> SuccessResponse[UserRead]:
    """Return the authenticated user's profile (§17)."""
    user = await users.get_by_id(current_user.user_id)
    if user is None:
        raise NotFoundError(message="User not found")
    return success_response(request, UserRead.model_validate(user))


@router.patch(
    "/me",
    response_model=SuccessResponse[UserRead],
    summary="Update the authenticated user's profile",
)
async def update_me(
    payload: UserUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> SuccessResponse[UserRead]:
    """Update editable profile fields (name, phone, avatar, locale)."""
    user = await service.update_user(
        current_user.user_id, **payload.model_dump(exclude_unset=True)
    )
    return success_response(request, UserRead.model_validate(user))


@router.post(
    "/me/change-password",
    response_model=SuccessResponse[UserRead],
    summary="Change the authenticated user's password",
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[UserRead]:
    """Change the password and sign out every other session (§17).

    The acting session (bound to the presented access token's ``jti``) stays
    valid; all other sessions are revoked.
    """
    ip_address, user_agent = _request_metadata(request)
    user = await service.change_password(
        user_id=current_user.user_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        current_session_jti=current_user.session_jti,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return success_response(request, UserRead.model_validate(user))


@router.get(
    "/me/sessions",
    response_model=SuccessResponse[list[SessionRead]],
    summary="List the authenticated user's active sessions",
)
async def list_sessions(
    request: Request,
    page: int = 1,
    limit: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> SuccessResponse[list[SessionRead]]:
    """Paginate the acting user's live, unexpired sessions (§17)."""
    page_result = await service.list_active_sessions(
        user_id=current_user.user_id, page=page, limit=limit
    )
    return success_response(
        request,
        [SessionRead.model_validate(item) for item in page_result.items],
        pagination=pagination_meta(page_result),
    )


@router.delete(
    "/me/sessions/{session_id}",
    response_model=SuccessResponse[SessionRead],
    summary="Revoke one of the authenticated user's sessions",
)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
    sessions: SessionRepository = Depends(get_session_repository),
) -> SuccessResponse[SessionRead]:
    """Revoke an owned session; repeated revokes are idempotent (§17, §25)."""
    session = await _require_owned_session(
        session_id, current_user.user_id, sessions
    )
    if session.revoked_at is None:
        session = await service.revoke_session(session_id=session_id)
    return success_response(request, SessionRead.model_validate(session))

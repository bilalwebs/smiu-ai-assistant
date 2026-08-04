"""Authentication endpoints (API_SPECIFICATION.md §3.3; BACKEND_ARCHITECTURE.md §9).

Purpose:
    Public, unauthenticated identity routes: student registration, email
    verification, credential login, refresh-token rotation, and logout.
    Login and refresh return a short-lived access JWT plus an opaque refresh
    token whose server-side session row is created in the same unit of work
    (DATABASE_DESIGN.md §25). ``remember_me`` extends the refresh-token
    lifetime; logout revokes the server-side session (§3.4, §5.5).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.dependencies.services import get_auth_service
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.response import SuccessResponse
from app.schemas.users import UserRead
from app.services import AuthService
from app.utils.response import success_response

router = APIRouter(prefix="/auth", tags=["auth"])


def _request_metadata(request: Request) -> tuple[str | None, str | None]:
    """Return ``(ip_address, user_agent)`` for audit/session attribution."""
    ip_address = request.client.host if request.client is not None else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


@router.post(
    "/register",
    response_model=SuccessResponse[UserRead],
    status_code=201,
    summary="Register a student account",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[UserRead]:
    """Create a pending student account and send a verification email (§3.3.1)."""
    ip_address, user_agent = _request_metadata(request)
    user = await service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        enrollment_no=payload.enrollment_no,
        department_id=payload.department_id,
        program_name=payload.program_name,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return success_response(request, UserRead.model_validate(user))


@router.post(
    "/verify-email",
    response_model=SuccessResponse[UserRead],
    summary="Verify an email address",
)
async def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[UserRead]:
    """Activate the account for a signed verification token."""
    ip_address, user_agent = _request_metadata(request)
    user = await service.verify_email(
        token=payload.token,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return success_response(request, UserRead.model_validate(user))


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    summary="Log in with credentials",
)
async def login(
    payload: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[TokenResponse]:
    """Authenticate and return an access + refresh token pair (§3.3.3)."""
    ip_address, user_agent = _request_metadata(request)
    result = await service.login(
        email=payload.email,
        password=payload.password,
        remember_me=payload.remember_me,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return success_response(
        request,
        TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type="bearer",
            expires_in=result.access_expires_in,
            refresh_expires_in=result.refresh_expires_in,
            user=UserRead.model_validate(result.user),
        ),
    )


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    summary="Rotate a refresh token into a new token pair",
)
async def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[TokenResponse]:
    """Rotate the refresh token; return a fresh access + refresh pair (§5.4)."""
    ip_address, user_agent = _request_metadata(request)
    result = await service.rotate_refresh(
        refresh_token=payload.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return success_response(
        request,
        TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type="bearer",
            expires_in=result.access_expires_in,
            refresh_expires_in=result.refresh_expires_in,
            user=UserRead.model_validate(result.user),
        ),
    )


@router.post(
    "/logout",
    response_model=SuccessResponse[None],
    summary="Log out the presented refresh token",
)
async def logout(
    payload: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[None]:
    """Revoke the session bound to the refresh token (§3.4)."""
    ip_address, user_agent = _request_metadata(request)
    await service.logout(
        refresh_token=payload.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return success_response(request, None)


@router.post(
    "/logout-all",
    response_model=SuccessResponse[dict[str, int]],
    summary="Log out every session of the authenticated user",
)
async def logout_all(
    payload: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[dict[str, int]]:
    """Revoke every session belonging to the refresh token's owner (§5.5)."""
    ip_address, user_agent = _request_metadata(request)
    revoked = await service.logout_all(
        refresh_token=payload.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return success_response(request, {"revoked": revoked})


@router.post(
    "/forgot-password",
    response_model=SuccessResponse[dict[str, str]],
    summary="Request a password-reset link",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[dict[str, str]]:
    """Send a single-use reset link; the response is generic (§16).

    The same response is returned whether or not the email exists, so account
    existence is never revealed (no enumeration).
    """
    ip_address, user_agent = _request_metadata(request)
    await service.forgot_password(
        email=payload.email,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return success_response(
        request,
        {
            "message": (
                "If that email address exists, a password reset link has "
                "been sent."
            )
        },
    )


@router.post(
    "/reset-password",
    response_model=SuccessResponse[UserRead],
    summary="Set a new password with a valid reset token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[UserRead]:
    """Reset the password, invalidate the token, and revoke all sessions (§16)."""
    ip_address, user_agent = _request_metadata(request)
    user = await service.reset_password(
        token=payload.token,
        new_password=payload.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return success_response(request, UserRead.model_validate(user))

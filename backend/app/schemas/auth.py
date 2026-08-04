"""Authentication schemas (API_SPECIFICATION.md §3.3, §5; Phase 6).

Purpose:
    Request/response payloads for the identity lifecycle endpoints. The
    password-strength policy (API_SPECIFICATION.md §12.5) is enforced here so
    invalid registrations fail fast at 422; the service re-checks it as
    defense-in-depth.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.security.password import password_policy_errors
from app.schemas.base import ApiModel
from app.schemas.users import UserRead


class RegisterRequest(BaseModel):
    """Student account registration payload (§3.3.1)."""

    email: EmailStr
    password: str
    full_name: str = Field(min_length=1, max_length=150)
    enrollment_no: str | None = Field(default=None, min_length=1, max_length=30)
    department_id: uuid.UUID | None = None
    program_name: str | None = Field(default=None, max_length=150)

    @field_validator("password")
    @classmethod
    def _validate_password_policy(cls, value: str) -> str:
        errors = password_policy_errors(value)
        if errors:
            joined = "; ".join(errors)
            raise ValueError(f"password {joined}")
        return value


class LoginRequest(BaseModel):
    """Credentials payload for ``POST /auth/login`` (§3.3.3)."""

    email: EmailStr
    password: str
    remember_me: bool = False


class VerifyEmailRequest(BaseModel):
    """Signed verification token payload for ``POST /auth/verify-email``."""

    token: str = Field(min_length=1)


class RefreshTokenRequest(BaseModel):
    """Opaque refresh-token payload for refresh/logout endpoints (§31.3)."""

    refresh_token: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    """Email payload for ``POST /auth/forgot-password`` (§16)."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """New-password payload for ``POST /auth/reset-password`` (§16).

    The reset token is single-use; ``password`` must satisfy the strength
    policy and ``confirm_password`` must match it.
    """

    token: str = Field(min_length=1)
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def _validate_password_policy(cls, value: str) -> str:
        errors = password_policy_errors(value)
        if errors:
            joined = "; ".join(errors)
            raise ValueError(f"password {joined}")
        return value

    @model_validator(mode="after")
    def _passwords_match(self) -> ResetPasswordRequest:
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password must match")
        return self


class ChangePasswordRequest(BaseModel):
    """Current + new password payload for ``POST /users/me/change-password`` (§17)."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _validate_new_password_policy(cls, value: str) -> str:
        errors = password_policy_errors(value)
        if errors:
            joined = "; ".join(errors)
            raise ValueError(f"new_password {joined}")
        return value


class TokenResponse(ApiModel):
    """Issued token pair plus the authenticated user (§3.3.3 response)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    user: UserRead


__all__ = [
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "RegisterRequest",
    "ResetPasswordRequest",
    "TokenResponse",
    "VerifyEmailRequest",
]

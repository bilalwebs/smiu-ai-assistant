"""User schemas (API_SPECIFICATION.md §17).

Purpose:
    Define the authenticated user profile payloads. Sensitive account columns
    (``password_hash``, lockout counters) are never exposed.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.models import UserRole, UserStatus
from app.schemas.base import ApiModel, UtcDateTime


class UserRead(ApiModel):
    """Authenticated user profile (API_SPECIFICATION.md §17)."""

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    email_verified_at: UtcDateTime | None = None
    phone: str | None = None
    avatar_url: str | None = None
    last_login_at: UtcDateTime | None = None
    locale: str
    preferences: dict[str, Any] | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class UserUpdate(BaseModel):
    """Editable profile fields for ``PATCH /users/me``."""

    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    avatar_url: str | None = Field(default=None)
    locale: str | None = Field(default=None, min_length=2, max_length=10)
    preferences: dict[str, Any] | None = None

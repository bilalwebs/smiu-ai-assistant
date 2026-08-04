"""``users`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §12).

Identity & Access: account creation, profile updates, and guarded
activation/deactivation lifecycle transitions. All persistence flows through
:class:`~app.repositories.users.UserRepository`; the service owns the unit of
work (BACKEND_ARCHITECTURE.md §12.3).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole, UserStatus
from app.repositories import Page, UserRepository
from app.services.base import BaseService
from app.services.exceptions import ConflictError, InvalidStateError, NotFoundError


class UserService(BaseService):
    """Account lifecycle operations for :class:`app.models.users.User`."""

    def __init__(
        self, session: AsyncSession, users: UserRepository | None = None
    ) -> None:
        super().__init__(session)
        self._users = users or UserRepository(session)

    async def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        role: UserRole = UserRole.STUDENT,
        status: UserStatus = UserStatus.PENDING,
        **profile: Any,
    ) -> User:
        """Create a new account after shape and uniqueness validation."""
        email = self._validate_not_blank(email, field="email").lower()
        full_name = self._validate_not_blank(full_name, field="full_name")
        self._validate_not_blank(password_hash, field="password_hash")
        role = self._validate_enum(role, UserRole, field="role")
        status = self._validate_enum(status, UserStatus, field="status")
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise ConflictError(
                message="A user with this email already exists",
                details=[{"field": "email", "reason": "already in use"}],
            )
        return await self._users.create(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            status=status,
            **profile,
        )

    async def update_user(self, user_id: uuid.UUID, **changes: Any) -> User:
        """Apply profile changes with per-field validation and uniqueness."""
        user = await self._require_user(user_id)
        if "email" in changes:
            email = self._validate_not_blank(changes["email"], field="email").lower()
            existing = await self._users.get_by_email(email)
            if existing is not None and existing.id != user_id:
                raise ConflictError(
                    message="A user with this email already exists",
                    details=[{"field": "email", "reason": "already in use"}],
                )
            changes["email"] = email
        if "full_name" in changes:
            changes["full_name"] = self._validate_not_blank(
                changes["full_name"], field="full_name"
            )
        if "password_hash" in changes:
            self._validate_not_blank(changes["password_hash"], field="password_hash")
        if "role" in changes:
            changes["role"] = self._validate_enum(
                changes["role"], UserRole, field="role"
            )
        if "status" in changes:
            changes["status"] = self._validate_enum(
                changes["status"], UserStatus, field="status"
            )
        return await self._users.update(user, **changes)

    async def activate_user(self, user_id: uuid.UUID) -> User:
        """Activate a non-active account."""
        user = await self._require_user(user_id)
        if user.status == UserStatus.ACTIVE:
            raise InvalidStateError(message="User is already active")
        return await self._users.update(user, status=UserStatus.ACTIVE)

    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        """Deactivate an active account."""
        user = await self._require_user(user_id)
        if user.status == UserStatus.DEACTIVATED:
            raise InvalidStateError(message="User is already deactivated")
        return await self._users.update(user, status=UserStatus.DEACTIVATED)

    async def list_users(
        self, *, page: int = 1, limit: int = 20
    ) -> Page[User]:
        """Paginate all users, newest first (admin-only, API_SPECIFICATION.md §25)."""
        return await self._users.paginate(
            page=page,
            limit=limit,
            order_by=[User.created_at.desc()],
        )

    async def _require_user(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="User not found")
        return user

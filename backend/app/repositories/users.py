"""``users`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §12).

Identity & Access: typed lookups for accounts, student-linked users, and the
active-user list. Sensitive columns (``password_hash``) are never included in
default projections; consumers must defer/load them explicitly when needed.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.sql.base import ExecutableOption

from app.models import Student, User, UserStatus
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access for :class:`app.models.users.User`."""

    model = User

    async def get_by_email(
        self, email: str, *, options: Sequence[ExecutableOption] = ()
    ) -> User | None:
        """Fetch a live user by email address."""
        return await self.get(User.email == email, options=options)

    async def get_by_student_id(
        self, student_id: uuid.UUID, *, options: Sequence[ExecutableOption] = ()
    ) -> User | None:
        """Fetch the user who owns the live student profile with ``student_id``."""
        stmt = (
            select(User)
            .join(Student, Student.user_id == User.id)
            .where(
                Student.id == student_id,
                User.deleted_at.is_(None),
                Student.deleted_at.is_(None),
            )
        )
        if options:
            stmt = stmt.options(*options)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_active_users(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> list[User]:
        """List live, active users, newest first."""
        return await self.list(
            User.status == UserStatus.ACTIVE,
            order_by=[User.created_at.desc()],
            limit=limit,
            offset=offset,
        )


__all__ = ["UserRepository"]

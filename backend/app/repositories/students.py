"""``students`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §13).

Identity & Access: typed lookups for the 1:1 academic profile of student-role
users.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.sql.base import ExecutableOption

from app.models import Student
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    """Data access for :class:`app.models.students.Student`."""

    model = Student

    async def get_by_user_id(
        self, user_id: uuid.UUID, *, options: Sequence[ExecutableOption] = ()
    ) -> Student | None:
        """Fetch the live student profile of a user."""
        return await self.get(Student.user_id == user_id, options=options)

    async def get_by_enrollment_no(
        self, enrollment_no: str, *, options: Sequence[ExecutableOption] = ()
    ) -> Student | None:
        """Fetch a live student by enrollment number."""
        return await self.get(
            Student.enrollment_no == enrollment_no, options=options
        )

    async def list_by_department(
        self,
        department_id: uuid.UUID,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Student]:
        """List live students in a department, newest first."""
        return await self.list(
            Student.department_id == department_id,
            order_by=[Student.created_at.desc()],
            limit=limit,
            offset=offset,
        )


__all__ = ["StudentRepository"]

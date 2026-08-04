"""``students`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §13).

Identity & Access: academic-profile creation and updates for student-role
users. A profile exists only when the owning user's role is ``student``
(DATABASE_DESIGN.md §13).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Student, UserRole
from app.repositories import DepartmentRepository, StudentRepository, UserRepository
from app.services.base import BaseService
from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class StudentService(BaseService):
    """Academic-profile operations for :class:`app.models.students.Student`."""

    def __init__(
        self,
        session: AsyncSession,
        students: StudentRepository | None = None,
        users: UserRepository | None = None,
        departments: DepartmentRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._students = students or StudentRepository(session)
        self._users = users or UserRepository(session)
        self._departments = departments or DepartmentRepository(session)

    async def create_student(
        self, *, user_id: uuid.UUID, enrollment_no: str, **profile: Any
    ) -> Student:
        """Create a student profile for a student-role user."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="User not found")
        if user.role != UserRole.STUDENT:
            raise BusinessRuleError(
                message="Only student-role users can have a student profile",
                details=[{"field": "user_id", "reason": "user role is not student"}],
            )
        if await self._students.get_by_user_id(user_id) is not None:
            raise ConflictError(
                message="A student profile already exists for this user",
                details=[{"field": "user_id", "reason": "profile already exists"}],
            )
        enrollment_no = self._validate_not_blank(enrollment_no, field="enrollment_no")
        if await self._students.get_by_enrollment_no(enrollment_no) is not None:
            raise ConflictError(
                message="This enrollment number is already in use",
                details=[{"field": "enrollment_no", "reason": "already in use"}],
            )
        return await self._students.create(
            user_id=user_id, enrollment_no=enrollment_no, **profile
        )

    async def assign_department(
        self, *, student_id: uuid.UUID, department_id: uuid.UUID
    ) -> Student:
        """Assign a student to a department."""
        student = await self._require_student(student_id)
        department = await self._departments.get_by_id(department_id)
        if department is None:
            raise NotFoundError(message="Department not found")
        if student.department_id == department_id:
            raise ConflictError(
                message="Student is already assigned to this department",
                details=[{"field": "department_id", "reason": "already assigned"}],
            )
        return await self._students.update(student, department_id=department_id)

    async def update_semester(
        self, *, student_id: uuid.UUID, current_semester: int
    ) -> Student:
        """Update a student's current semester (1-16)."""
        student = await self._require_student(student_id)
        if not 1 <= current_semester <= 16:
            raise ValidationError(
                message="current_semester must be between 1 and 16",
                details=[{"field": "current_semester", "reason": "out of range"}],
            )
        return await self._students.update(
            student, current_semester=current_semester
        )

    async def _require_student(self, student_id: uuid.UUID) -> Student:
        student = await self._students.get_by_id(student_id)
        if student is None:
            raise NotFoundError(message="Student not found")
        return student

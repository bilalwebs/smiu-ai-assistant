"""``students`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import UserRole
from app.services import StudentService
from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


async def test_create_student_happy_path(student_service, user_factory) -> None:
    user = await user_factory()
    student = await student_service.create_student(
        user_id=user.id, enrollment_no="SMIU-2024-001"
    )
    assert student.user_id == user.id
    assert student.enrollment_no == "SMIU-2024-001"
    assert student.status.value == "active"


async def test_create_student_missing_user_raises_not_found(
    student_service: StudentService,
) -> None:
    with pytest.raises(NotFoundError):
        await student_service.create_student(
            user_id=uuid.uuid4(), enrollment_no="SMIU-2024-999"
        )


async def test_create_student_non_student_role_raises(
    student_service, user_factory
) -> None:
    user = await user_factory(role=UserRole.ADMIN)
    with pytest.raises(BusinessRuleError):
        await student_service.create_student(
            user_id=user.id, enrollment_no="SMIU-2024-998"
        )


async def test_create_student_duplicate_profile_raises(
    student_service, user_factory
) -> None:
    user = await user_factory()
    await student_service.create_student(
        user_id=user.id, enrollment_no="SMIU-2024-001"
    )
    with pytest.raises(ConflictError):
        await student_service.create_student(
            user_id=user.id, enrollment_no="SMIU-2024-002"
        )


async def test_create_student_duplicate_enrollment_raises(
    student_service, user_factory
) -> None:
    user = await user_factory()
    other = await user_factory()
    await student_service.create_student(
        user_id=user.id, enrollment_no="SMIU-2024-001"
    )
    with pytest.raises(ConflictError):
        await student_service.create_student(
            user_id=other.id, enrollment_no="SMIU-2024-001"
        )


async def test_assign_department_happy_path(
    student_service, department_service, user_factory
) -> None:
    user = await user_factory()
    student = await student_service.create_student(
        user_id=user.id, enrollment_no="SMIU-2024-001"
    )
    dept = await department_service.create_department(
        code="CS", name="Computer Science"
    )
    updated = await student_service.assign_department(
        student_id=student.id, department_id=dept.id
    )
    assert updated.department_id == dept.id


async def test_assign_department_missing_student_raises(
    student_service, department_service
) -> None:
    dept = await department_service.create_department(
        code="CS", name="Computer Science"
    )
    with pytest.raises(NotFoundError):
        await student_service.assign_department(
            student_id=uuid.uuid4(), department_id=dept.id
        )


async def test_assign_department_missing_department_raises(
    student_service, user_factory
) -> None:
    user = await user_factory()
    student = await student_service.create_student(
        user_id=user.id, enrollment_no="SMIU-2024-001"
    )
    with pytest.raises(NotFoundError):
        await student_service.assign_department(
            student_id=student.id, department_id=uuid.uuid4()
        )


async def test_assign_department_already_assigned_raises(
    student_service, department_service, user_factory
) -> None:
    user = await user_factory()
    student = await student_service.create_student(
        user_id=user.id, enrollment_no="SMIU-2024-001"
    )
    dept = await department_service.create_department(
        code="CS", name="Computer Science"
    )
    await student_service.assign_department(
        student_id=student.id, department_id=dept.id
    )
    with pytest.raises(ConflictError):
        await student_service.assign_department(
            student_id=student.id, department_id=dept.id
        )


async def test_update_semester_happy_path(student_service, user_factory) -> None:
    user = await user_factory()
    student = await student_service.create_student(
        user_id=user.id, enrollment_no="SMIU-2024-001"
    )
    updated = await student_service.update_semester(
        student_id=student.id, current_semester=3
    )
    assert updated.current_semester == 3


async def test_update_semester_out_of_range_raises(
    student_service, user_factory
) -> None:
    user = await user_factory()
    student = await student_service.create_student(
        user_id=user.id, enrollment_no="SMIU-2024-001"
    )
    with pytest.raises(ValidationError):
        await student_service.update_semester(
            student_id=student.id, current_semester=17
        )


async def test_update_semester_missing_student_raises(
    student_service: StudentService,
) -> None:
    with pytest.raises(NotFoundError):
        await student_service.update_semester(
            student_id=uuid.uuid4(), current_semester=1
        )

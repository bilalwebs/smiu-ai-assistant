"""``departments`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.services import DepartmentService
from app.services.exceptions import ConflictError, NotFoundError, ValidationError


async def test_create_department_happy_path(
    department_service: DepartmentService,
) -> None:
    dept = await department_service.create_department(
        code="cs", name="Computer Science"
    )
    assert dept.code == "CS"
    assert dept.name == "Computer Science"
    assert dept.is_active is True


async def test_create_department_duplicate_code_raises(
    department_service: DepartmentService,
) -> None:
    await department_service.create_department(code="CS", name="Computer Science")
    with pytest.raises(ConflictError):
        await department_service.create_department(
            code="CS", name="Software Engineering"
        )


async def test_create_department_duplicate_name_raises(
    department_service: DepartmentService,
) -> None:
    await department_service.create_department(code="CS", name="Computer Science")
    with pytest.raises(ConflictError):
        await department_service.create_department(
            code="SE", name="Computer Science"
        )


async def test_create_department_blank_name_raises(
    department_service: DepartmentService,
) -> None:
    with pytest.raises(ValidationError):
        await department_service.create_department(code="CS", name="   ")


async def test_assign_hod_happy_path(department_service: DepartmentService) -> None:
    dept = await department_service.create_department(
        code="CS", name="Computer Science"
    )
    updated = await department_service.assign_hod(
        department_id=dept.id, head_name="Dr. Ayesha"
    )
    assert updated.head_name == "Dr. Ayesha"


async def test_assign_hod_missing_department_raises(
    department_service: DepartmentService,
) -> None:
    with pytest.raises(NotFoundError):
        await department_service.assign_hod(
            department_id=uuid.uuid4(), head_name="Dr. Ayesha"
        )


async def test_assign_hod_blank_head_name_raises(
    department_service: DepartmentService,
) -> None:
    dept = await department_service.create_department(
        code="CS", name="Computer Science"
    )
    with pytest.raises(ValidationError):
        await department_service.assign_hod(department_id=dept.id, head_name="")

"""``departments`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §14).

Organization: department and routing-target management. Routing is data-driven,
so services validate uniqueness but never hard-code department identifiers.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department
from app.repositories import DepartmentRepository
from app.services.base import BaseService
from app.services.exceptions import ConflictError, NotFoundError


class DepartmentService(BaseService):
    """Department and routing-target operations for
    :class:`app.models.departments.Department`.
    """

    def __init__(
        self,
        session: AsyncSession,
        departments: DepartmentRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._departments = departments or DepartmentRepository(session)

    async def create_department(
        self, *, code: str, name: str, **profile: Any
    ) -> Department:
        """Create a department after code/name uniqueness validation."""
        code = self._validate_not_blank(code, field="code").strip().upper()
        name = self._validate_not_blank(name, field="name")
        if await self._departments.get_by_code(code) is not None:
            raise ConflictError(
                message="A department with this code already exists",
                details=[{"field": "code", "reason": "already in use"}],
            )
        if await self._departments.get(Department.name == name) is not None:
            raise ConflictError(
                message="A department with this name already exists",
                details=[{"field": "name", "reason": "already in use"}],
            )
        return await self._departments.create(code=code, name=name, **profile)

    async def assign_hod(
        self, *, department_id: uuid.UUID, head_name: str
    ) -> Department:
        """Assign a head of department."""
        department = await self._require_department(department_id)
        head_name = self._validate_not_blank(head_name, field="head_name")
        return await self._departments.update(department, head_name=head_name)

    async def _require_department(self, department_id: uuid.UUID) -> Department:
        department = await self._departments.get_by_id(department_id)
        if department is None:
            raise NotFoundError(message="Department not found")
        return department

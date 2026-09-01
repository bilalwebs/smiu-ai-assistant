"""Department endpoints.

Purpose:
    Public read-only endpoint for listing active departments so the
    registration form can populate the department dropdown from the
    database instead of hard-coding values.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.dependencies.database import get_db_session
from app.repositories.departments import DepartmentRepository
from app.schemas.response import SuccessResponse
from app.utils.response import success_response

router = APIRouter(prefix="/departments", tags=["departments"])


class DepartmentRead:
    """Minimal read model for public department listing."""

    def __init__(self, id: str, code: str, name: str) -> None:
        self.id = id
        self.code = code
        self.name = name


@router.get(
    "",
    response_model=SuccessResponse[list[dict[str, str]]],
    summary="List active departments",
)
async def list_departments(
    request: Request,
    db=Depends(get_db_session),
) -> SuccessResponse[list[dict[str, str]]]:
    """Return all active departments for the registration dropdown."""
    repo = DepartmentRepository(db)
    departments = await repo.list_active()
    data = [
        {"id": str(d.id), "code": d.code, "name": d.name}
        for d in departments
    ]
    return success_response(request, data)

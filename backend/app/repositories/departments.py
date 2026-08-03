"""``departments`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §14).

Organization: typed lookups for routing targets. Routing is data-driven, so
repositories never hard-code department identifiers.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.sql.base import ExecutableOption

from app.models import Department
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    """Data access for :class:`app.models.departments.Department`."""

    model = Department

    async def get_by_code(
        self, code: str, *, options: Sequence[ExecutableOption] = ()
    ) -> Department | None:
        """Fetch a live department by its unique code."""
        return await self.get(Department.code == code, options=options)

    async def list_active(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> list[Department]:
        """List active departments in display order."""
        return await self.list(
            Department.is_active.is_(True),
            order_by=[Department.sort_order.asc(), Department.name.asc()],
            limit=limit,
            offset=offset,
        )


__all__ = ["DepartmentRepository"]

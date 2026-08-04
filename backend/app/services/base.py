"""Service base (BACKEND_ARCHITECTURE.md §11, §12.3, §13).

Purpose:
    Provide the shared transaction surface and validation helpers every service
    builds on. Services own the unit-of-work boundary: they coordinate
    repositories and commit exactly once on success. Repositories never commit
    (BACKEND_ARCHITECTURE.md §12.3, §13).

Usage:
    ``class UserService(BaseService): ...``; callers use the ``commit`` /
    ``rollback`` / ``flush`` / ``refresh`` helpers to manage the transaction.
"""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.exceptions import ValidationError

_T = TypeVar("_T")
_E = TypeVar("_E", bound=Enum)


class BaseService:
    """Shared transaction and validation surface for services."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- transaction control ------------------------------------------------

    async def commit(self) -> None:
        """Commit the current unit of work (services own the boundary)."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Abandon the current unit of work."""
        await self._session.rollback()

    async def flush(self) -> None:
        """Send pending changes to the database without committing."""
        await self._session.flush()

    async def refresh(self, entity: _T) -> _T:
        """Expire and reload a single entity from the database."""
        await self._session.refresh(entity)
        return entity

    # -- validation helpers -------------------------------------------------

    @staticmethod
    def _validate_not_blank(value: str | None, *, field: str) -> str:
        """Return ``value`` trimmed, or raise a 422 when blank."""
        if value is None or not value.strip():
            raise ValidationError(
                message=f"{field} must not be blank",
                details=[{"field": field, "reason": "must not be blank"}],
            )
        return value.strip()

    @staticmethod
    def _validate_enum(value: object, enum_type: type[_E], *, field: str) -> _E:
        """Coerce ``value`` to a member of ``enum_type``, or raise a 422."""
        try:
            return enum_type(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                message=f"{field} is invalid",
                details=[{"field": field, "reason": "not a valid choice"}],
            ) from exc

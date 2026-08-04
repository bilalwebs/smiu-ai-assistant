"""Generic repository base (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §26, §31, §34).

Purpose:
    Provide the typed CRUD/query surface every model repository shares so Phase 3
    repositories only implement intent-named helpers, never raw SQL.

Responsibilities:
    - CRUD plus reusable typed query helpers (``list``, ``paginate``,
      ``paginate_keyset``, ``count``, ``exists``).
    - Automatic soft-delete scoping (``deleted_at IS NULL``) for soft-deletable
      models (DATABASE_DESIGN.md §26). Append-only tables (no ``deleted_at``)
      are never scoped.
    - Optimistic-concurrency guard for versioned models (§34.5).
    - Never commits, rolls back, or closes the session — transaction boundaries
      belong to the caller's unit of work (§12.3, §13).

Usage:
    ``class UserRepository(BaseRepository[User]): model = User``.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Any, Protocol, TypeVar, cast

from sqlalchemy import Column, ColumnElement, Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper, class_mapper
from sqlalchemy.sql.base import ExecutableOption

from app.database.base import Base
from app.models.mixins import VersionMixin

_S = TypeVar("_S", bound=Select[Any])

_SQLITE_TS_FORMAT = "%Y-%m-%d %H:%M:%S"

#: Maximum allowed page size to prevent unbounded query resource usage.
MAX_PAGE_LIMIT = 100

class SoftDeletable(Protocol):
    """Runtime-shape of :class:`app.models.mixins.SoftDeleteMixin`."""

    deleted_at: datetime | None

    @property
    def is_deleted(self) -> bool: ...

    def soft_delete(self) -> None: ...

    def restore(self) -> None: ...


class Versioned(Protocol):
    """Runtime-shape of :class:`app.models.mixins.VersionMixin`."""

    def increment_version(self) -> None: ...


class _Keyed(Protocol):
    """``created_at``/``id`` shape shared by every model."""

    created_at: datetime
    id: uuid.UUID


@dataclass(frozen=True)
class Page[T]:
    """Offset-based pagination result (API_SPECIFICATION.md §9)."""

    items: list[T]
    page: int
    limit: int
    offset: int
    total: int
    total_pages: int
    next_page: int | None
    prev_page: int | None


KeysetCursor = tuple[datetime, uuid.UUID]


@dataclass(frozen=True)
class KeysetPage[T]:
    """Keyset-paginated slice ordered by ``(created_at, id)`` (DATABASE_DESIGN.md §31)."""

    items: list[T]
    next_cursor: KeysetCursor | None
    has_more: bool


class BaseRepository[T: Base]:
    """Typed CRUD/query base for a single ORM entity.

    One repository per aggregate/domain entity (BACKEND_ARCHITECTURE.md §12.2).
    Repositories expose intent-named methods, never raw query builders, and do
    not implement business rules or flows.
    """

    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._mapper: Mapper[T] = class_mapper(self.model)
        self._has_soft_delete = "deleted_at" in self._mapper.columns
        self._has_version = issubclass(self.model, VersionMixin)

    # -- internals -----------------------------------------------------------

    def _column(self, name: str) -> Column[Any]:
        return self._mapper.columns[name]

    def _scope(self, stmt: _S) -> _S:
        """Apply the default live-row scope for soft-deletable models (§26)."""
        if self._has_soft_delete:
            return stmt.where(self._column("deleted_at").is_(None))
        return stmt

    def _select(
        self,
        *,
        filters: Sequence[ColumnElement[bool]] = (),
        order_by: Sequence[Any] = (),
        options: Sequence[ExecutableOption] = (),
    ) -> Select[tuple[T]]:
        stmt = self._scope(select(self.model))
        if filters:
            stmt = stmt.where(*filters)
        if order_by:
            stmt = stmt.order_by(*order_by)
        if options:
            stmt = stmt.options(*options)
        return stmt

    @property
    def _dialect_name(self) -> str:
        bind = self._session.bind
        return bind.dialect.name if bind is not None else "sqlite"

    def _keyset_time_expr(self, created_at: Column[Any]) -> ColumnElement[Any]:
        """Normalize the ``created_at`` key to stored precision on SQLite.

        SQLite's ``CURRENT_TIMESTAMP`` stores second precision, while bound
        datetime parameters always carry microseconds, so the cursor's equality
        anchor would never match a stored value. PostgreSQL round-trips
        timestamps unchanged and needs no normalization.
        """
        if self._dialect_name == "sqlite":
            return func.strftime(_SQLITE_TS_FORMAT, created_at)
        return created_at

    def _keyset_cursor_time(
        self, cursor_created_at: datetime
    ) -> ColumnElement[str] | datetime:
        if self._dialect_name == "sqlite":
            return func.strftime(_SQLITE_TS_FORMAT, cursor_created_at)
        return cursor_created_at

    # -- write operations ----------------------------------------------------

    async def create(self, **values: Any) -> T:
        """Build, persist (flush), and return a new entity."""
        return await self.add(self.model(**values))

    async def add(self, entity: T) -> T:
        """Persist an existing instance and reload its database defaults."""
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity: T, **values: Any) -> T:
        """Apply attribute updates, bump ``version`` when present, and flush."""
        for key, value in values.items():
            if not hasattr(entity, key):
                raise ValueError(f"{self.model.__name__} has no attribute {key!r}")
            setattr(entity, key, value)
        if self._has_version:
            cast(Versioned, entity).increment_version()
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """Hard-delete a row. Reserved for append-only cleanup; soft-deletable
        models should prefer :meth:`soft_delete`."""
        await self._session.delete(entity)
        await self._session.flush()

    async def soft_delete(self, entity: T) -> T:
        """Mark a row as deleted without removing it (§26)."""
        if not self._has_soft_delete:
            raise TypeError(f"{self.model.__name__} is not soft-deletable")
        cast(SoftDeletable, entity).soft_delete()
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def restore(self, entity: T) -> T:
        """Clear the soft-delete marker, returning a row to live (§26)."""
        if not self._has_soft_delete:
            raise TypeError(f"{self.model.__name__} is not soft-deletable")
        cast(SoftDeletable, entity).restore()
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    # -- read operations -----------------------------------------------------

    async def get(
        self,
        *filters: ColumnElement[bool],
        order_by: Sequence[Any] = (),
        options: Sequence[ExecutableOption] = (),
    ) -> T | None:
        """Return the first matching live row, or ``None``."""
        stmt = self._select(filters=filters, order_by=order_by, options=options)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_one(
        self,
        *filters: ColumnElement[bool],
        order_by: Sequence[Any] = (),
        options: Sequence[ExecutableOption] = (),
    ) -> T:
        """Return exactly one matching live row; raises when none or many."""
        stmt = self._select(filters=filters, order_by=order_by, options=options)
        result = await self._session.execute(stmt)
        return result.scalars().one()

    async def get_by_id(
        self, entity_id: uuid.UUID, *, options: Sequence[ExecutableOption] = ()
    ) -> T | None:
        """Fetch a live row by primary key, or ``None``."""
        return await self.get(self._column("id") == entity_id, options=options)

    async def list(
        self,
        *filters: ColumnElement[bool],
        order_by: Sequence[Any] = (),
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """Return matching live rows with optional limit/offset."""
        stmt = self._select(filters=filters, order_by=order_by, options=options)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def count(self, *filters: ColumnElement[bool]) -> int:
        """Count matching live rows."""
        stmt = self._scope(select(func.count()).select_from(self.model))
        if filters:
            stmt = stmt.where(*filters)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def exists(self, *filters: ColumnElement[bool]) -> bool:
        """Return ``True`` when at least one live row matches."""
        return await self.count(*filters) > 0

    # -- pagination ----------------------------------------------------------

    async def paginate(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        filters: Sequence[ColumnElement[bool]] = (),
        order_by: Sequence[Any] = (),
        options: Sequence[ExecutableOption] = (),
    ) -> Page[T]:
        """Offset-based page per API_SPECIFICATION.md §9 (public contract)."""
        page = max(1, page)
        limit = max(1, min(limit, MAX_PAGE_LIMIT))
        total = await self.count(*filters)
        total_pages = ceil(total / limit) if total else 0
        offset = (page - 1) * limit
        items = await self.list(
            *filters, order_by=order_by, options=options, limit=limit, offset=offset
        )
        return Page(
            items=items,
            page=page,
            limit=limit,
            offset=offset,
            total=total,
            total_pages=total_pages,
            next_page=page + 1 if page < total_pages else None,
            prev_page=page - 1 if page > 1 else None,
        )

    async def paginate_keyset(
        self,
        *,
        limit: int = 20,
        cursor: KeysetCursor | None = None,
        filters: Sequence[ColumnElement[bool]] = (),
        options: Sequence[ExecutableOption] = (),
        descending: bool = True,
    ) -> KeysetPage[T]:
        """Keyset page on ``(created_at, id)`` for large collections (§31)."""
        limit = max(1, min(limit, MAX_PAGE_LIMIT))
        created_at = self._column("created_at")
        id_col = self._column("id")
        stmt = self._select(filters=filters, options=options)
        time_key = self._keyset_time_expr(created_at)
        if descending:
            stmt = stmt.order_by(time_key.desc(), id_col.desc())
        else:
            stmt = stmt.order_by(time_key.asc(), id_col.asc())
        if cursor is not None:
            cursor_created_at, cursor_id = cursor
            cursor_time = self._keyset_cursor_time(cursor_created_at)
            if descending:
                stmt = stmt.where(
                    or_(
                        time_key < cursor_time,
                        and_(time_key == cursor_time, id_col < cursor_id),
                    )
                )
            else:
                stmt = stmt.where(
                    or_(
                        time_key > cursor_time,
                        and_(time_key == cursor_time, id_col > cursor_id),
                    )
                )
        stmt = stmt.limit(limit + 1)
        result = await self._session.scalars(stmt)
        rows = list(result.all())
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor: KeysetCursor | None = None
        if has_more and items:
            last = cast(_Keyed, items[-1])
            next_cursor = (last.created_at, last.id)
        return KeysetPage(items=items, next_cursor=next_cursor, has_more=has_more)

    # -- session helpers -----------------------------------------------------

    async def flush(self) -> None:
        """Send pending changes to the database without committing."""
        await self._session.flush()

    async def refresh(self, entity: T) -> T:
        """Expire and reload a single entity from the database."""
        await self._session.refresh(entity)
        return entity


__all__ = [
    "BaseRepository",
    "KeysetCursor",
    "KeysetPage",
    "Page",
]

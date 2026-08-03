"""Persistence-layer exception types (DATABASE_DESIGN.md §30, §34).

Purpose:
    Define the exceptions raised by the database layer — connection failures,
    integrity violations, and optimistic-lock conflicts — so repositories and
    services can translate them to the typed application errors in
    :mod:`app.exceptions` at the boundary (BACKEND_ARCHITECTURE.md §15).

Usage:
    ``raise DatabaseUnavailableError("...")`` inside the persistence layer;
    the service boundary maps these to ``ServiceUnavailableError`` /
    ``ConflictError`` as appropriate.
"""

from __future__ import annotations


class DatabaseError(Exception):
    """Base class for all persistence-layer errors."""


class DatabaseUnavailableError(DatabaseError):
    """The database could not be reached or is not accepting connections."""


class DataIntegrityError(DatabaseError):
    """A constraint, uniqueness, or type-level integrity rule was violated."""


class OptimisticLockError(DatabaseError):
    """A write raced against a stale ``version`` (DATABASE_DESIGN.md §34.5)."""

    def __init__(self, *, entity: str, expected: int, actual: int) -> None:
        super().__init__(
            f"{entity} version conflict: expected {expected}, found {actual}"
        )
        self.entity = entity
        self.expected = expected
        self.actual = actual

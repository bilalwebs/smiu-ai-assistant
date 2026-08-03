"""Database-layer constants (DATABASE_DESIGN.md §3, §27).

Purpose:
    Single home for stable identifiers and defaults shared across the
    persistence layer so driver, pool, and probe values never drift between
    modules (PROJECT_RULES.md Coding Standards).
"""

from __future__ import annotations

SQLITE_BACKEND = "sqlite"
POSTGRESQL_BACKEND = "postgresql"

DEFAULT_VERSION = 1

DB_READY_PROBE = "SELECT 1"

"""Database package.

Purpose:
    Own SQLAlchemy wiring for the backend (DATABASE_DESIGN.md §27, §30):
    the declarative base, async engine/session factory, health probes, and
    migration helpers.

Responsibilities:
    - ``base``: the single ``Base`` all ORM models inherit from, with the
      constraint/index naming convention applied to every schema.
    - ``session``: lazily-created async engine + session factory driven by
      settings, with pool configuration and a test reset hook.
    - ``health``: reusable async connectivity probe for readiness checks.
    - ``migration_helpers``: idempotent introspection helpers for revisions.
    - ``constants`` / ``exceptions`` / ``utils``: shared persistence-layer
      values, error types, and URL helpers.

Usage:
    Models import ``Base`` from :mod:`app.database.base` and compose the mixins
    from :mod:`app.models`; sessions come from :mod:`app.database.session`.
    The ORM model mixins and combined ``BaseModel`` land in Phase 2A; concrete
    business models arrive in Phase 3.
"""

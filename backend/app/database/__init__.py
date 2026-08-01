"""Database package.

Purpose:
    Own SQLAlchemy wiring for the backend (DATABASE_DESIGN.md §27, §30):
    the declarative base, async engine, and session factory.

Responsibilities:
    - Provide the single ``Base`` all ORM models inherit from.
    - Expose a lazily-created async engine driven by settings.
    - Provide ``SessionLocal`` for request-scoped sessions and a test reset hook.

Usage:
    Models import ``Base`` from :mod:`app.database.base`; sessions come from
    :mod:`app.database.session`. No model files exist yet (Phase 2).
"""

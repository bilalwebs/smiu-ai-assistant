"""Dependency injection package.

Purpose:
    Own FastAPI dependency providers shared across routers
    (BACKEND_ARCHITECTURE.md §15.2).

Responsibilities:
    - Provide ``get_settings`` so any endpoint/service can access config.
    - Provide the async database session generator ``get_db_session``.
    - Centralize provider registration for testability.

Usage:
    Routers declare parameters like
    ``settings: Settings = Depends(get_settings)`` or
    ``db: AsyncSession = Depends(get_db_session)``.
"""

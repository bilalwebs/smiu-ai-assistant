"""API package.

Purpose:
    Own the versioned REST API surface (BACKEND_ARCHITECTURE.md §5.1, §17;
    API_SPECIFICATION.md §3).

Responsibilities:
    - Aggregate versioned sub-routers into a single base ``router``.
    - Nest resources under ``/api/v1`` via :mod:`app.api.v1`.
    - Keep route handlers thin; business logic lives in services.

Usage:
    ``api.router`` is mounted by the application factory; the versioned
    sub-routers are nested inside it.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import api_router as v1_router

router = APIRouter()
router.include_router(v1_router)

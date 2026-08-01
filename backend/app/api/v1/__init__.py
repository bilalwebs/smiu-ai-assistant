"""API version v1 package.

Purpose:
    Versioned v1 API — routes nested under ``/api/v1``
    (API_SPECIFICATION.md §3; BACKEND_ARCHITECTURE.md §17).

Responsibilities:
    - Aggregate all v1 endpoint routers into a single ``api_router``.
    - Declare the shared v1 dependencies/tags.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router)

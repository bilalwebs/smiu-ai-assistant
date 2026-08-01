"""FastAPI application entrypoint for the SMU AI Assistant backend service.

Purpose:
    Expose the WSGI/ASGI application object for ``uvicorn``
    (BACKEND_ARCHITECTURE.md §15.1; IMPLEMENTATION_PLAN.md Phase 1).

Usage:
    Run locally with ``uvicorn app.main:app --reload`` from ``backend/``.
"""

from __future__ import annotations

from app.core.app_factory import create_app

app = create_app()

"""FastAPI application factory.

Purpose:
    Compose the FastAPI application from settings, middleware, exception
    handlers, routers, and lifespan lifecycle (BACKEND_ARCHITECTURE.md §15-17).

Responsibilities:
    - Build the app with the active environment's settings and docs gates.
    - Register middleware in the documented order.
    - Register the centralized exception handlers.
    - Mount the versioned API (``/api/v1``) and orchestration health aliases.
    - Run startup/shutdown lifecycle (logging setup, sqlite data dir, engine
      disposal).

Usage:
    ``app = create_app()`` in ``app.main``. Tests pass an explicit
    ``settings`` instance.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api import router as api_base_router
from app.api.v1.endpoints.health import orchestration_router
from app.config.settings import Environment, Settings, get_settings
from app.core.constants import API_V1_PREFIX
from app.core.logging import setup_logging
from app.database.session import reset_engine
from app.exceptions.handlers import register_exception_handlers
from app.middleware.cors import register_cors
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


def _ensure_sqlite_directory(settings: Settings) -> None:
    """Create the parent directory for a file-backed sqlite database."""
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy.engine import make_url

    database = make_url(settings.database_url).database
    if database is None or database == ":memory:":
        return
    parent = Path(database.lstrip("/")).parent
    if str(parent) != ".":
        parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = app.state.settings
    setup_logging(settings)
    _ensure_sqlite_directory(settings)
    logger.info(
        "Application started",
        extra={
            "environment": settings.environment.value,
            "version": settings.version,
        },
    )
    try:
        yield
    finally:
        reset_engine()
        logger.info("Application shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application for the given settings."""
    active_settings = settings or get_settings()

    app = FastAPI(
        title=active_settings.app_name,
        version=active_settings.version,
        description="SMIU AI Assistant backend API",
        docs_url=active_settings.docs_url,
        redoc_url=active_settings.redoc_url,
        openapi_url=active_settings.openapi_url,
        lifespan=_lifespan,
    )
    app.state.settings = active_settings

    # Innermost first; Starlette applies middleware in reverse registration
    # order, so the last added wrapper is the outermost.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        RequestIDMiddleware,
        request_id_header=active_settings.request_id_header,
        correlation_id_header=active_settings.correlation_id_header,
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=active_settings.environment is Environment.PRODUCTION,
    )
    register_cors(app, active_settings)

    register_exception_handlers(app)

    app.include_router(api_base_router, prefix=API_V1_PREFIX)
    app.include_router(orchestration_router)

    return app

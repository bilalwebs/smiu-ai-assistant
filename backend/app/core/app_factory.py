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

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_base_router
from app.api.v1.endpoints.health import orchestration_router
from app.config.settings import Environment, Settings, get_settings
from app.core.constants import API_V1_PREFIX
from app.core.logging import setup_logging
from app.database.session import reset_engine
from app.exceptions.handlers import register_exception_handlers
from app.middleware.cors import register_cors
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware, RateLimitRule
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parents[2] / "static"


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
        docs_url=None,
        redoc_url=None,
        openapi_url=active_settings.openapi_url,
        lifespan=_lifespan,
    )
    app.state.settings = active_settings

    # Self-hosted docs UI: Swagger UI / ReDoc assets are vendored under
    # ``static/docs`` and served from this backend, so the UI works without
    # CDN access and the strict API CSP never needs to allow third parties.
    if (active_settings.docs_url or active_settings.redoc_url) and _STATIC_DIR.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=_STATIC_DIR),
            name="static",
        )

    async def _swagger_ui_html(request: Request) -> HTMLResponse:
        root_path = request.scope.get("root_path", "").rstrip("/")
        openapi_url = root_path + str(active_settings.openapi_url or "/openapi.json")
        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title=f"{active_settings.app_name} - Swagger UI",
            swagger_js_url="/static/docs/swagger-ui-bundle.js",
            swagger_css_url="/static/docs/swagger-ui.css",
            swagger_favicon_url="/static/docs/favicon-32x32.png",
        )

    async def _redoc_html(request: Request) -> HTMLResponse:
        root_path = request.scope.get("root_path", "").rstrip("/")
        openapi_url = root_path + str(active_settings.openapi_url or "/openapi.json")
        return get_redoc_html(
            openapi_url=openapi_url,
            title=f"{active_settings.app_name} - ReDoc",
            redoc_js_url="/static/docs/redoc.standalone.js",
            redoc_favicon_url="/static/docs/favicon-32x32.png",
            with_google_fonts=False,
        )

    if active_settings.docs_url:
        app.add_api_route(
            active_settings.docs_url,
            _swagger_ui_html,
            include_in_schema=False,
        )
    if active_settings.redoc_url:
        app.add_api_route(
            active_settings.redoc_url,
            _redoc_html,
            include_in_schema=False,
        )

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
        relaxed_paths=(
            active_settings.docs_url or "/docs",
            active_settings.redoc_url or "/redoc",
            "/static/",
        ),
    )
    register_cors(app, active_settings)

    rate_limit_rules = {
        "/api/v1/auth/login": RateLimitRule(
            max_requests=active_settings.login_rate_limit,
            window_seconds=active_settings.login_rate_window,
        ),
        "/api/v1/auth/register": RateLimitRule(
            max_requests=active_settings.register_rate_limit,
            window_seconds=active_settings.register_rate_window,
        ),
        "/api/v1/auth/forgot-password": RateLimitRule(
            max_requests=active_settings.forgot_password_rate_limit,
            window_seconds=active_settings.forgot_password_rate_window,
        ),
        "/api/v1/auth/reset-password": RateLimitRule(
            max_requests=active_settings.reset_password_rate_limit,
            window_seconds=active_settings.reset_password_rate_window,
        ),
    }
    app.add_middleware(RateLimitMiddleware, rules=rate_limit_rules)

    register_exception_handlers(app)

    app.include_router(api_base_router, prefix=API_V1_PREFIX)
    app.include_router(orchestration_router)

    return app

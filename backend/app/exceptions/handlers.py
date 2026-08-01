"""Centralized exception handlers.

Purpose:
    Provide the single, application-wide translation of every exception into the
    documented error envelope (BACKEND_ARCHITECTURE.md §15; API_SPECIFICATION.md §8).

Responsibilities:
    - Translate ``AppError`` to its configured status/code/message.
    - Translate framework ``HTTPException`` via a status-to-code mapping.
    - Translate Pydantic validation errors to ``422`` with field-level details.
    - Translate unexpected exceptions to a generic ``500`` (full detail logged).
    - Never expose stack traces or internal details to clients.

Usage:
    ``register_exception_handlers(app)`` is called by the application factory.
"""

from __future__ import annotations

import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.constants import DEFAULT_ERROR_CODE, HTTP_STATUS_ERROR_CODES
from app.exceptions.app_error import AppError
from app.schemas.response import ErrorBody, ErrorDetail, ErrorResponse
from app.utils.request_id import get_request_id
from app.utils.response import build_meta

logger = logging.getLogger(__name__)

_VALIDATION_CODE = "VAL002"
_VALIDATION_MESSAGE = "Request validation failed"
_CONTEXT_LOCATIONS = ("body", "query", "path", "header", "cookie")


def _loc_to_field(loc: tuple[object, ...]) -> str:
    """Flatten a Pydantic error location into a ``snake_case`` field path."""
    parts = [str(part) for part in loc if part not in _CONTEXT_LOCATIONS]
    return ".".join(parts) if parts else "request"


def _error_json(
    *,
    status_code: int,
    code: str,
    message: str,
    request: Request,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details),
        meta=build_meta(request),
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Translate an application error into the standard envelope."""
    app_error = cast(AppError, exc)
    return _error_json(
        status_code=app_error.status_code,
        code=app_error.code,
        message=app_error.message,
        request=request,
        details=(
            [ErrorDetail(**detail) for detail in app_error.details]
            if app_error.details
            else None
        ),
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Translate a framework HTTP exception into the standard envelope."""
    http_exc = cast(StarletteHTTPException, exc)
    detail = http_exc.detail if isinstance(http_exc.detail, str) else "HTTP request failed"
    return _error_json(
        status_code=http_exc.status_code,
        code=HTTP_STATUS_ERROR_CODES.get(http_exc.status_code, DEFAULT_ERROR_CODE),
        message=detail,
        request=request,
    )


async def request_validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Translate Pydantic validation errors into a 422 with field details."""
    validation_exc = cast(RequestValidationError, exc)
    details = [
        ErrorDetail(
            field=_loc_to_field(err.get("loc", ())),
            reason=str(err.get("msg", "")),
        )
        for err in validation_exc.errors()
    ]
    return _error_json(
        status_code=422,
        code=_VALIDATION_CODE,
        message=_VALIDATION_MESSAGE,
        request=request,
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Translate unexpected exceptions into a generic 500 (logged in full)."""
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        extra={"request_id": get_request_id(request), "path": request.url.path},
    )
    return _error_json(
        status_code=500,
        code=DEFAULT_ERROR_CODE,
        message="Internal server error",
        request=request,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

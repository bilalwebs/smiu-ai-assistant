"""Response envelope builders.

Purpose:
    Provide the single construction path for success and error envelopes so
    that the response/error format (API_SPECIFICATION.md §7-8) is never
    assembled by hand inside a router or handler.

Responsibilities:
    - Build ``meta`` (request id + UTC timestamp) from the current request.
    - Build success envelopes around arbitrary payloads.
    - Build error envelopes as JSON responses for exception handlers.

Usage:
    Endpoints return ``success_response(request, data)``; exception handlers
    return ``error_response(request, code=..., message=..., status_code=...)``.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.schemas.response import (
    ErrorBody,
    ErrorResponse,
    PaginationMeta,
    ResponseMeta,
    SuccessResponse,
)
from app.utils.request_id import get_request_id
from app.utils.time import utc_now


def build_meta(
    request: Request, pagination: PaginationMeta | None = None
) -> ResponseMeta:
    """Build response metadata from the current request context."""
    return ResponseMeta(
        request_id=get_request_id(request),
        timestamp=utc_now(),
        pagination=pagination,
    )


def success_response(
    request: Request,
    data: Any,
    *,
    pagination: PaginationMeta | None = None,
) -> SuccessResponse[Any]:
    """Return a standard success envelope around ``data``."""
    return SuccessResponse(data=data, meta=build_meta(request, pagination))


def error_response(
    request: Request,
    *,
    code: str,
    message: str,
    status_code: int,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    """Return a standard error envelope as a JSON response."""
    payload = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details),
        meta=build_meta(request),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))

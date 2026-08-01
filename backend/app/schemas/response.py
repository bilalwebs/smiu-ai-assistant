"""Global API response and error envelope schemas.

Purpose:
    Implement the single response envelope and error envelope defined in
    API_SPECIFICATION.md §7 and §8 so every endpoint returns one consistent
    shape.

Responsibilities:
    - Define ``SuccessResponse`` (success / data / meta) for all success payloads.
    - Define ``ErrorResponse`` (success / error / meta) for all failures.
    - Define the ``meta`` structure (request id, UTC timestamp, pagination).

Usage:
    Use ``SuccessResponse[T]`` as a FastAPI ``response_model`` and build
    instances with :func:`app.utils.response.success_response`. Error envelopes
    are produced centrally by :mod:`app.exceptions.handlers`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer


class PaginationMeta(BaseModel):
    """Pagination metadata embedded in ``meta`` for collection responses."""

    page: int
    limit: int
    offset: int
    total: int
    total_pages: int
    next_page: int | None
    prev_page: int | None


class ResponseMeta(BaseModel):
    """Operational metadata carried on every response (API_SPECIFICATION.md §7.4)."""

    request_id: str
    timestamp: datetime
    pagination: PaginationMeta | None = None

    @field_serializer("timestamp")
    def _serialize_timestamp(self, value: datetime) -> str:
        """Serialize timestamps as UTC ISO-8601 with a ``Z`` suffix."""
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class SuccessResponse[T](BaseModel):
    """Standard success envelope: ``success`` + ``data`` + ``meta``."""

    success: Literal[True] = True
    data: T
    meta: ResponseMeta


class ErrorDetail(BaseModel):
    """Field-level validation context (API_SPECIFICATION.md §32.2)."""

    field: str
    reason: str


class ErrorBody(BaseModel):
    """Error body: stable code, human-readable message, optional detail list."""

    code: str = Field(pattern=r"^[A-Z]{3}[0-9]{3}$")
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope: ``success`` + ``error`` + ``meta``."""

    success: Literal[False] = False
    error: ErrorBody
    meta: ResponseMeta

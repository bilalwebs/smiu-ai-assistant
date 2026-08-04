"""Service-layer exception types (BACKEND_ARCHITECTURE.md §15).

Purpose:
    Define the typed errors services raise for business-rule, lifecycle, and
    lookup failures. Service errors subclass the application error types in
    :mod:`app.exceptions.app_error` so the global handler renders the
    documented envelope (API_SPECIFICATION.md §26-27) without per-service
    formatting.

Usage:
    ``raise ConflictError(message="...")`` from a service; a boundary handler
    may catch these by type when it must branch on the specific failure.
"""

from __future__ import annotations

from app.core.constants import HTTP_STATUS_ERROR_CODES
from app.exceptions import app_error


class NotFoundError(app_error.NotFoundError):
    """A referenced resource does not exist (HTTP 404)."""

    def __init__(
        self,
        *,
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            code=HTTP_STATUS_ERROR_CODES[404], message=message, details=details
        )


class ConflictError(app_error.ConflictError):
    """A uniqueness or state conflict was detected (HTTP 409)."""

    def __init__(
        self,
        *,
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            code=HTTP_STATUS_ERROR_CODES[409], message=message, details=details
        )


class ValidationError(app_error.ValidationError):
    """A business validation rule failed (HTTP 422)."""

    def __init__(
        self,
        *,
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(code="VAL001", message=message, details=details)


class InvalidStateError(ValidationError):
    """A state-transition or lifecycle rule was violated (HTTP 422)."""


class BusinessRuleError(ValidationError):
    """A domain business-rule violation (HTTP 422)."""


__all__ = [
    "BusinessRuleError",
    "ConflictError",
    "InvalidStateError",
    "NotFoundError",
    "ValidationError",
]

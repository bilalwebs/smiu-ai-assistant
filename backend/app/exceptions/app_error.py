"""Typed application exceptions.

Purpose:
    Define the exception hierarchy that business and infrastructure code raise
    so the global handler can map them to the documented error envelope with
    stable error codes (API_SPECIFICATION.md §26).

Responsibilities:
    - Provide a base ``AppError`` carrying code, message, status, and details.
    - Provide semantic subclasses for the common HTTP categories.

Usage:
    Services raise these instead of catching-and-formatting ad hoc; the global
    handler in :mod:`app.exceptions.handlers` translates them.
"""

from __future__ import annotations

from app.core.constants import DEFAULT_ERROR_CODE


class AppError(Exception):
    """Base class for all application-level errors."""

    def __init__(
        self,
        *,
        code: str = DEFAULT_ERROR_CODE,
        message: str,
        status_code: int = 500,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    """Requested resource does not exist (HTTP 404)."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=404, details=details)


class ConflictError(AppError):
    """Request conflicts with the current state (HTTP 409)."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=409, details=details)


class UnauthorizedError(AppError):
    """Missing or invalid credentials (HTTP 401)."""

    def __init__(
        self,
        *,
        code: str = "AUTH001",
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=401, details=details)


class ForbiddenError(AppError):
    """Authenticated but not permitted (HTTP 403)."""

    def __init__(
        self,
        *,
        code: str = "AUTH003",
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=403, details=details)


class ValidationError(AppError):
    """Business-layer validation failure (HTTP 422)."""

    def __init__(
        self,
        *,
        code: str = "VAL001",
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=422, details=details)


class ServiceUnavailableError(AppError):
    """A required dependency is unavailable (HTTP 503)."""

    def __init__(
        self,
        *,
        code: str = "SYS003",
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=503, details=details)


class RateLimitError(AppError):
    """Too many requests — rate limit exceeded (HTTP 429)."""

    def __init__(
        self,
        *,
        retry_after: int = 60,
        message: str = "Too many requests. Please try again later.",
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            code="SYS002",
            message=message,
            status_code=429,
            details=details,
        )
        self.retry_after = retry_after

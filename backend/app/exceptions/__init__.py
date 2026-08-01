"""Exception handling package.

Purpose:
    Own the typed exception hierarchy and the centralized, application-wide
    exception handlers (BACKEND_ARCHITECTURE.md §15).

Responsibilities:
    - Define domain/infrastructure exception types with stable error codes.
    - Translate exceptions into the standard error envelope.
    - Never leak stack traces to clients.

Usage:
    Raise ``AppError`` subclasses from services; handlers registered by
    :func:`app.exceptions.handlers.register_exception_handlers` produce the
    error responses.
"""

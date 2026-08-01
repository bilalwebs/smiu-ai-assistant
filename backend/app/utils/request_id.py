"""Request id / correlation id helpers.

Purpose:
    Centralize request id generation, validation, and retrieval so middleware,
    exception handlers, and response builders agree on one id per request.

Responsibilities:
    - Generate a fresh request id (UUID hex) when none is supplied.
    - Validate incoming correlation ids to prevent header injection.
    - Read the active request id from ``request.state``.

Usage:
    ``generate_request_id()`` for new ids; ``get_request_id(request)`` inside
    handlers and exception handlers.
"""

from __future__ import annotations

import re
from typing import cast
from uuid import uuid4

from starlette.requests import Request

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

_UNKNOWN = "unknown"


def generate_request_id() -> str:
    """Return a new 32-character request id (UUID v4 hex)."""
    return uuid4().hex


def is_valid_request_id(value: str) -> bool:
    """Return whether ``value`` is an acceptable incoming correlation id."""
    return bool(_REQUEST_ID_PATTERN.fullmatch(value))


def get_request_id(request: Request) -> str:
    """Return the request id stored on the request state, or ``"unknown"``."""
    return cast(str, getattr(request.state, "request_id", None) or _UNKNOWN)

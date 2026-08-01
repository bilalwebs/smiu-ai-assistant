"""Application-wide constants.

Purpose:
    Single home for stable identifiers shared across the backend so values
    never drift between modules (PROJECT_RULES.md Coding Standards).

Responsibilities:
    - Define the versioned API prefix and OpenAPI metadata.
    - Map HTTP status codes to stable application error codes
      (API_SPECIFICATION.md §26-27) for the framework exception fallback.
    - Define the default error code for unexpected failures.
"""

from __future__ import annotations

APP_NAME = "smiu-ai-assistant-backend"
API_V1_PREFIX = "/api/v1"

DEFAULT_ERROR_CODE = "SYS001"

HTTP_STATUS_ERROR_CODES: dict[int, str] = {
    400: "VAL001",
    401: "AUTH001",
    403: "AUTH003",
    404: "VAL001",
    405: "VAL001",
    409: "REQ004",
    422: "VAL001",
    429: "SYS002",
    500: "SYS001",
    503: "SYS003",
}

MAX_REQUEST_ID_LENGTH = 64

"""Centralized logging (BACKEND_ARCHITECTURE.md §16).

Purpose:
    Own the logging configuration and formatters for the backend service.

Responsibilities:
    - Configure structured, level-based logging once per process (idempotent).
    - Provide a JSON formatter for production and a readable console formatter.
    - Redact sensitive fields (secrets, tokens, keys) before output.

Usage:
    Call ``setup_logging(settings)`` at application creation, then use the
    standard ``logging.getLogger(__name__)`` pattern throughout the codebase.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

from app.config.settings import Environment, Settings

_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(Authorization\s*:\s*Bearer\s+)[^\s,]+", re.IGNORECASE),
        r"\1***",
    ),
    (
        re.compile(
            r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key)"
            r"(\s*[:=]\s*)[^\s,]+"
        ),
        r"\1\2***",
    ),
)

_EXTRA_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "client_host",
    "environment",
)

_configured = False


def redact(text: str) -> str:
    """Replace known secret patterns with ``***`` in ``text``."""
    for pattern, replacement in _REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _collect_extras(record: logging.LogRecord) -> dict[str, object]:
    return {
        key: getattr(record, key)
        for key in _EXTRA_FIELDS
        if getattr(record, key, None) is not None
    }


class JsonFormatter(logging.Formatter):
    """Structured JSON formatter for production log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        payload.update(_collect_extras(record))
        if record.exc_info:
            payload["exc_info"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter for development environments."""

    _BASE = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    def __init__(self) -> None:
        super().__init__(self._BASE)

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        extras = _collect_extras(record)
        if extras:
            suffix = " ".join(f"{key}={value}" for key, value in extras.items())
            message = f"{message} ({suffix})"
        return redact(message)


def setup_logging(settings: Settings) -> None:
    """Configure root logging for the given settings (idempotent)."""
    global _configured
    if _configured:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    handler = logging.StreamHandler()
    if settings.environment is Environment.PRODUCTION:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())
    root_logger.addHandler(handler)

    # The request-logging middleware already emits structured access logs.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _configured = True


def reset_logging() -> None:
    """Reset the configured flag so tests can reconfigure logging."""
    global _configured
    _configured = False

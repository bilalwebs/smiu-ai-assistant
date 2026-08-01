"""Settings dependency.

Purpose:
    Provide the cached application settings to routes and services via FastAPI
    dependency injection (BACKEND_ARCHITECTURE.md §15.2).

Responsibilities:
    - Delegate to the module-level settings cache so one instance is shared.
    - Return the configured ``Settings`` subtype for the active environment.
"""

from __future__ import annotations

from collections.abc import Iterator

from app.config.settings import Settings
from app.config.settings import get_settings as get_configured_settings


def get_settings() -> Iterator[Settings]:
    """Yield the cached application settings."""
    yield get_configured_settings()

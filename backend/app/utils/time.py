"""Time utilities.

Purpose:
    Provide a single source for timestamp generation so all envelopes and logs
    use the same timezone (UTC).

Responsibilities:
    - Return timezone-aware UTC ``datetime`` values.

Usage:
    ``from app.utils.time import utc_now``.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)

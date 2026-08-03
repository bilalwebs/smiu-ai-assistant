"""Database health check utilities (DATABASE_DESIGN.md §27; API_SPECIFICATION.md §24).

Purpose:
    Provide a reusable async database probe so the readiness endpoint and any
    future health/telemetry consumer share one implementation, one probe, and
    one timeout policy instead of embedding raw ``SELECT 1`` calls in routers.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.constants import DB_READY_PROBE

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseHealth:
    """Result of a single database connectivity probe."""

    status: str
    latency_ms: float | None = None
    error: str | None = None

    @property
    def is_up(self) -> bool:
        return self.status == "up"


async def check_database_health(session: AsyncSession) -> DatabaseHealth:
    """Probe the database with ``SELECT 1`` and report status and latency.

    Returns ``DatabaseHealth(status="up", latency_ms=...)`` on success and
    ``DatabaseHealth(status="down", error=...)`` when the probe fails; it never
    raises.
    """
    started = time.perf_counter()
    try:
        await session.execute(text(DB_READY_PROBE))
    except Exception as exc:
        logger.warning("Database health probe failed", exc_info=exc)
        return DatabaseHealth(status="down", error=str(exc))
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    return DatabaseHealth(status="up", latency_ms=latency_ms)

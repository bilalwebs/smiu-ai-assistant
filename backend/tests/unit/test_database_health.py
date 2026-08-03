"""Database health utility tests (API_SPECIFICATION.md §24).

Verifies the reusable async probe reports ``up`` for a reachable database and
``down`` (with an error, never raising) when the connection is unavailable.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.health import DatabaseHealth, check_database_health


class _BrokenSession:
    async def execute(self, statement: object) -> None:
        raise ConnectionError("connection refused")


async def test_health_up_for_reachable_database(db_session: AsyncSession) -> None:
    health = await check_database_health(db_session)
    assert health.status == "up"
    assert health.is_up is True
    assert health.error is None
    assert health.latency_ms is not None
    assert health.latency_ms >= 0


async def test_health_down_reports_error_never_raises() -> None:
    broken = cast(AsyncSession, _BrokenSession())
    health = await check_database_health(broken)
    assert health.status == "down"
    assert health.is_up is False
    assert health.error == "connection refused"
    assert health.latency_ms is None


def test_health_dataclass_defaults() -> None:
    assert DatabaseHealth(status="up").is_up is True
    assert DatabaseHealth(status="down").is_up is False

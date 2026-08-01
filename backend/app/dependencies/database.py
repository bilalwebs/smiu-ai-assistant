"""Database session dependency.

Purpose:
    Provide a request-scoped async SQLAlchemy session and commit/rollback
    lifecycle (BACKEND_ARCHITECTURE.md §11, §15.2).

Responsibilities:
    - Open one session per request.
    - Commit on success, rollback on failure, always close in ``finally``.

Usage:
    Routes depend on ``db: AsyncSession = Depends(get_db_session)`` and commit
    through the session lifecycle; service layer owns transaction decisions.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async session with commit/rollback handling."""
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    else:
        await session.commit()
    finally:
        await session.close()

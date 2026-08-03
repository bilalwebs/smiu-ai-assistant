"""``sessions`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §25).

Identity & Access: refresh-token session lookups, revocation, active-session
listing, and expired-session purging. ``refresh_token_hash`` is never included
in default projections.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.sql.base import ExecutableOption

from app.models import UserSession
from app.repositories.base import BaseRepository
from app.utils.time import utc_now


class SessionRepository(BaseRepository[UserSession]):
    """Data access for :class:`app.models.sessions.UserSession`."""

    model = UserSession

    async def get_by_refresh_hash(
        self, refresh_token_hash: str, *, options: Sequence[ExecutableOption] = ()
    ) -> UserSession | None:
        """Fetch a session by its persisted refresh-token hash."""
        return await self.get(
            UserSession.refresh_token_hash == refresh_token_hash, options=options
        )

    async def revoke_session(self, session: UserSession) -> UserSession:
        """Revoke a session immediately (logout/password change, §25)."""
        return await self.update(session, revoked_at=utc_now())

    async def get_active_sessions(
        self,
        user_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[UserSession]:
        """List a user's live, unexpired sessions, most recently used first."""
        now = utc_now()
        return await self.list(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
            order_by=[UserSession.last_used_at.desc()],
            options=options,
            limit=limit,
            offset=offset,
        )

    async def delete_expired(self, before: datetime | None = None) -> int:
        """Hard-delete sessions expired before ``before`` (default now).

        Retention callers pass the 90-day purge cutoff from DATABASE_DESIGN.md §35.
        The statement skips identity-map synchronization (``synchronize_session``
        evaluates criteria in Python, which breaks on driver-coerced timestamp
        tzinfo); purged rows are expired by the caller's unit of work.
        """
        cutoff = before or utc_now()
        result = await self._session.execute(
            delete(UserSession)
            .where(UserSession.expires_at < cutoff)
            .execution_options(synchronize_session=False)
        )
        await self._session.flush()
        return result.rowcount or 0


__all__ = ["SessionRepository"]

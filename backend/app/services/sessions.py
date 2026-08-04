"""``sessions`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §25).

Identity & Access: refresh-token session creation and revocation. Access
tokens are stateless JWTs; refresh tokens are persisted hashed only (§25).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserSession
from app.repositories import Page, SessionRepository, UserRepository
from app.services.base import BaseService
from app.services.exceptions import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from app.utils.time import utc_now


class SessionService(BaseService):
    """Refresh-token session lifecycle (DATABASE_DESIGN.md §25)."""

    def __init__(
        self,
        session: AsyncSession,
        sessions: SessionRepository | None = None,
        users: UserRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._sessions = sessions or SessionRepository(session)
        self._users = users or UserRepository(session)

    async def create_session(
        self,
        *,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        device_name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        access_jti: str | None = None,
    ) -> UserSession:
        """Create a server-side session for a valid refresh-token hash."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        refresh_token_hash = self._validate_not_blank(
            refresh_token_hash, field="refresh_token_hash"
        )
        if len(refresh_token_hash) > 64:
            raise ValidationError(
                message="refresh_token_hash must be at most 64 characters",
                details=[{"field": "refresh_token_hash", "reason": "too long"}],
            )
        if expires_at <= utc_now():
            raise ValidationError(
                message="expires_at must be in the future",
                details=[{"field": "expires_at", "reason": "must be in the future"}],
            )
        if await self._sessions.get_by_refresh_hash(refresh_token_hash) is not None:
            raise ConflictError(
                message="A session with this refresh token already exists",
                details=[{"field": "refresh_token_hash", "reason": "already in use"}],
            )
        return await self._sessions.create(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
            access_jti=access_jti,
        )

    async def revoke_session(self, *, session_id: uuid.UUID) -> UserSession:
        """Revoke a single session; raises when already revoked."""
        session = await self._require_session(session_id)
        if session.revoked_at is not None:
            raise InvalidStateError(message="Session is already revoked")
        return await self._sessions.revoke_session(session)

    async def revoke_all_sessions(self, *, user_id: uuid.UUID) -> int:
        """Revoke every active session of a user; returns the count revoked."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        active = await self._sessions.get_active_sessions(user_id)
        for session in active:
            await self._sessions.revoke_session(session)
        return len(active)

    async def revoke_other_sessions(
        self, *, user_id: uuid.UUID, except_jti: str | None
    ) -> int:
        """Revoke a user's active sessions except the one bound to ``except_jti``.

        Used by the change-password flow so the acting session survives while
        every other device is signed out (API_SPECIFICATION.md §17). Returns
        the number of sessions revoked.
        """
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        active = await self._sessions.get_active_sessions(user_id)
        count = 0
        for session in active:
            if session.access_jti == except_jti:
                continue
            await self._sessions.revoke_session(session)
            count += 1
        return count

    async def list_active_sessions(
        self,
        *,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> Page[UserSession]:
        """Paginate a user's live, unexpired sessions, most recently used first."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        now = utc_now()
        return await self._sessions.paginate(
            page=page,
            limit=limit,
            filters=[
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            ],
            order_by=[UserSession.last_used_at.desc()],
        )

    async def _require_session(self, session_id: uuid.UUID) -> UserSession:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise NotFoundError(message="Session not found")
        return session

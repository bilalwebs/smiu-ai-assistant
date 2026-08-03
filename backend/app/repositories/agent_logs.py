"""``agent_logs`` repository (BACKEND_ARCHITECTURE.md §12; AI_ARCHITECTURE.md §11.2, §30.1).

Append-only agent routing/execution log. Rows are never edited by application
code.
"""

from __future__ import annotations

import uuid

from app.models import AgentLog
from app.repositories.base import BaseRepository


class AgentLogRepository(BaseRepository[AgentLog]):
    """Data access for :class:`app.models.agent_logs.AgentLog`."""

    model = AgentLog

    async def list_by_conversation(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AgentLog]:
        """List a conversation's agent runs, newest first."""
        return await self.list(
            AgentLog.conversation_id == conversation_id,
            order_by=[AgentLog.created_at.desc()],
            limit=limit,
            offset=offset,
        )


__all__ = ["AgentLogRepository"]

"""``ai_conversations`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §15).

AI & Knowledge: chat-session history and the message window used to rebuild
conversation context for the AI layer.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.sql.base import ExecutableOption

from app.models import AIConversation, ChatMessage
from app.repositories.base import BaseRepository, Page


class ConversationRepository(BaseRepository[AIConversation]):
    """Data access for :class:`app.models.ai_conversations.AIConversation`."""

    model = AIConversation

    async def get_history(
        self, user_id: uuid.UUID, *, page: int = 1, limit: int = 20
    ) -> Page[AIConversation]:
        """Paginate a user's conversations, most recently active first."""
        return await self.paginate(
            page=page,
            limit=limit,
            filters=[AIConversation.user_id == user_id],
            order_by=[AIConversation.last_message_at.desc()],
        )

    async def get_recent_messages(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int = 50,
        options: Sequence[ExecutableOption] = (),
    ) -> list[ChatMessage]:
        """Return the newest ``limit`` live messages, in oldest-first order."""
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.deleted_at.is_(None),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        if options:
            stmt = stmt.options(*options)
        result = await self._session.scalars(stmt)
        return list(reversed(result.all()))


__all__ = ["ConversationRepository"]

"""``chat_history`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §16).

AI & Knowledge: message-level access within a conversation. All message roles,
streaming lifecycle states, and RAG citations originate here.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.sql.base import ExecutableOption

from app.models import ChatMessage
from app.repositories.base import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Data access for :class:`app.models.chat_history.ChatMessage`."""

    model = ChatMessage

    async def list_by_conversation(
        self,
        conversation_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ChatMessage]:
        """List a conversation's live messages in chronological order."""
        return await self.list(
            ChatMessage.conversation_id == conversation_id,
            order_by=[ChatMessage.created_at.asc()],
            options=options,
            limit=limit,
            offset=offset,
        )


__all__ = ["ChatMessageRepository"]

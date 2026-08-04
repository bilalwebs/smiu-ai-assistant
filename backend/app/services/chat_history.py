"""``chat_history`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §16).

AI & Knowledge: the single message-append path within a conversation, which also
maintains conversation counters, message-history reads, and streaming status
transitions. Allowed role/status combinations mirror the ``status_roles_check``
constraint (DATABASE_DESIGN.md §16; ui-ux-design.md §36).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentKey,
    ChatMessage,
    ConversationStatus,
    MessageRole,
    MessageStatus,
)
from app.repositories import ChatMessageRepository, ConversationRepository
from app.services.base import BaseService
from app.services.exceptions import InvalidStateError, NotFoundError, ValidationError
from app.utils.time import utc_now

_ROLE_STATUSES: dict[MessageRole, frozenset[MessageStatus]] = {
    MessageRole.USER: frozenset({MessageStatus.COMPLETED, MessageStatus.ERROR}),
    MessageRole.SYSTEM: frozenset({MessageStatus.COMPLETED, MessageStatus.ERROR}),
    MessageRole.TOOL: frozenset({MessageStatus.COMPLETED, MessageStatus.ERROR}),
    MessageRole.ASSISTANT: frozenset(
        {
            MessageStatus.QUEUED,
            MessageStatus.STREAMING,
            MessageStatus.COMPLETED,
            MessageStatus.STOPPED,
        }
    ),
}


class ChatHistoryService(BaseService):
    """Message operations for :class:`app.models.chat_history.ChatMessage`."""

    def __init__(
        self,
        session: AsyncSession,
        messages: ChatMessageRepository | None = None,
        conversations: ConversationRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._messages = messages or ChatMessageRepository(session)
        self._conversations = conversations or ConversationRepository(session)

    async def add_message(
        self,
        *,
        conversation_id: uuid.UUID,
        role: MessageRole,
        content: str,
        status: MessageStatus = MessageStatus.COMPLETED,
        agent_key: AgentKey | None = None,
        content_format: str = "markdown",
        model: str | None = None,
        token_usage: dict[str, Any] | None = None,
        latency_ms: int | None = None,
        error_code: str | None = None,
        parent_message_id: uuid.UUID | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> ChatMessage:
        """Append a message to an active conversation and bump its counters."""
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError(message="Conversation not found")
        if conversation.status != ConversationStatus.ACTIVE:
            raise InvalidStateError(
                message="Messages can only be added to active conversations"
            )
        role = self._validate_enum(role, MessageRole, field="role")
        status = self._validate_enum(status, MessageStatus, field="status")
        content = self._validate_not_blank(content, field="content")
        content_format = self._validate_not_blank(content_format, field="content_format")
        if len(content_format) > 20:
            raise ValidationError(
                message="content_format must be at most 20 characters",
                details=[{"field": "content_format", "reason": "too long"}],
            )
        if latency_ms is not None and latency_ms < 0:
            raise ValidationError(
                message="latency_ms must not be negative",
                details=[{"field": "latency_ms", "reason": "negative"}],
            )
        self._assert_role_status(role, status)
        if parent_message_id is not None:
            parent = await self._messages.get_by_id(parent_message_id)
            if parent is None or parent.conversation_id != conversation_id:
                raise ValidationError(
                    message="parent_message_id must reference a message in this conversation",
                    details=[{"field": "parent_message_id", "reason": "invalid parent"}],
                )
        values: dict[str, Any] = {
            "conversation_id": conversation_id,
            "role": role,
            "agent_key": agent_key,
            "content": content,
            "content_format": content_format,
            "status": status,
            "model": model,
            "token_usage": token_usage,
            "latency_ms": latency_ms,
            "error_code": error_code,
            "parent_message_id": parent_message_id,
        }
        if metadata_ is not None:
            values["metadata_"] = metadata_
        message = await self._messages.create(**values)
        await self._conversations.update(
            conversation,
            message_count=conversation.message_count + 1,
            last_message_at=utc_now(),
        )
        return message

    async def get_history(
        self, *, conversation_id: uuid.UUID, limit: int = 50
    ) -> list[ChatMessage]:
        """Return a conversation's live messages in chronological order."""
        if await self._conversations.get_by_id(conversation_id) is None:
            raise NotFoundError(message="Conversation not found")
        return await self._messages.list_by_conversation(conversation_id, limit=limit)

    async def update_message_status(
        self,
        *,
        message_id: uuid.UUID,
        status: MessageStatus,
        error_code: str | None = None,
    ) -> ChatMessage:
        """Transition a message's streaming state (ui-ux-design.md §36)."""
        message = await self._messages.get_by_id(message_id)
        if message is None:
            raise NotFoundError(message="Message not found")
        status = self._validate_enum(status, MessageStatus, field="status")
        self._assert_role_status(message.role, status)
        if status == MessageStatus.ERROR and error_code is not None:
            return await self._messages.update(message, status=status, error_code=error_code)
        return await self._messages.update(message, status=status)

    @staticmethod
    def _assert_role_status(role: MessageRole, status: MessageStatus) -> None:
        """Reject a role/status pair the ``status_roles_check`` forbids."""
        if status not in _ROLE_STATUSES[role]:
            raise ValidationError(
                message=f"Status {status.value} is not valid for {role.value} messages",
                details=[{"field": "status", "reason": "invalid role/status combination"}],
            )

"""``ai_conversations`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §15).

AI & Knowledge: chat-session lifecycle — creation (with an optional first
message), rename/update, archive/restore, soft delete, and history reads.
Message writes beyond the initial seed belong to
:mod:`app.services.chat_history` (DATABASE_DESIGN.md §16).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentKey,
    AIConversation,
    ChatMessage,
    ConversationStatus,
    MessageRole,
    MessageStatus,
)
from app.repositories import (
    ChatMessageRepository,
    ConversationRepository,
    DepartmentRepository,
    Page,
    UserRepository,
)
from app.services.base import BaseService
from app.services.exceptions import InvalidStateError, NotFoundError, ValidationError
from app.utils.time import utc_now


class ConversationService(BaseService):
    """Lifecycle operations for :class:`app.models.ai_conversations.AIConversation`."""

    def __init__(
        self,
        session: AsyncSession,
        conversations: ConversationRepository | None = None,
        messages: ChatMessageRepository | None = None,
        users: UserRepository | None = None,
        departments: DepartmentRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._conversations = conversations or ConversationRepository(session)
        self._messages = messages or ChatMessageRepository(session)
        self._users = users or UserRepository(session)
        self._departments = departments or DepartmentRepository(session)

    async def create_conversation(
        self,
        *,
        user_id: uuid.UUID,
        department_id: uuid.UUID | None = None,
        title: str | None = None,
        summary: str | None = None,
        status: ConversationStatus = ConversationStatus.ACTIVE,
        current_agent: AgentKey | None = None,
        first_message: str | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> AIConversation:
        """Create a chat session, optionally seeded with the first user message."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        if (
            department_id is not None
            and await self._departments.get_by_id(department_id) is None
        ):
            raise NotFoundError(message="Department not found")
        title = (
            self._validate_not_blank(title, field="title")
            if title is not None
            else None
        )
        summary = (
            self._validate_not_blank(summary, field="summary")
            if summary is not None
            else None
        )
        status = self._validate_enum(status, ConversationStatus, field="status")
        if status != ConversationStatus.ACTIVE:
            raise ValidationError(
                message="Conversations can only be created as active",
                details=[{"field": "status", "reason": "not an initial state"}],
            )
        if current_agent is not None:
            current_agent = self._validate_enum(
                current_agent, AgentKey, field="current_agent"
            )
        values: dict[str, Any] = {
            "user_id": user_id,
            "department_id": department_id,
            "title": title,
            "summary": summary,
            "status": status,
            "current_agent": current_agent,
        }
        if metadata_ is not None:
            values["metadata_"] = metadata_
        conversation = await self._conversations.create(**values)
        if first_message is not None:
            await self._append_first_message(
                conversation,
                self._validate_not_blank(first_message, field="first_message"),
            )
        return conversation

    async def update_conversation(
        self, *, conversation_id: uuid.UUID, **changes: Any
    ) -> AIConversation:
        """Update title/summary/status/current_agent with per-field validation."""
        conversation = await self._require_conversation(conversation_id)
        if "title" in changes:
            changes["title"] = (
                self._validate_not_blank(changes["title"], field="title")
                if changes["title"] is not None
                else None
            )
        if "summary" in changes:
            changes["summary"] = (
                self._validate_not_blank(changes["summary"], field="summary")
                if changes["summary"] is not None
                else None
            )
        if "status" in changes:
            changes["status"] = self._validate_enum(
                changes["status"], ConversationStatus, field="status"
            )
        if "current_agent" in changes:
            changes["current_agent"] = (
                self._validate_enum(
                    changes["current_agent"], AgentKey, field="current_agent"
                )
                if changes["current_agent"] is not None
                else None
            )
        return await self._conversations.update(conversation, **changes)

    async def archive_conversation(
        self, *, conversation_id: uuid.UUID
    ) -> AIConversation:
        """Archive an active conversation (API_SPECIFICATION.md §22)."""
        conversation = await self._require_conversation(conversation_id)
        if conversation.status != ConversationStatus.ACTIVE:
            raise InvalidStateError(
                message=f"Conversation is already {conversation.status.value}"
            )
        return await self._conversations.update(
            conversation, status=ConversationStatus.ARCHIVED
        )

    async def restore_conversation(
        self, *, conversation_id: uuid.UUID
    ) -> AIConversation:
        """Restore an archived conversation (API_SPECIFICATION.md §22)."""
        conversation = await self._require_conversation(conversation_id)
        if conversation.status != ConversationStatus.ARCHIVED:
            raise InvalidStateError(
                message=f"Conversation is not archived (currently {conversation.status.value})"
            )
        return await self._conversations.update(
            conversation, status=ConversationStatus.ACTIVE
        )

    async def delete_conversation(
        self, *, conversation_id: uuid.UUID
    ) -> AIConversation:
        """Soft-delete a conversation (DATABASE_DESIGN.md §26)."""
        conversation = await self._require_conversation(conversation_id)
        return await self._conversations.soft_delete(conversation)

    async def get_conversation(self, *, conversation_id: uuid.UUID) -> AIConversation:
        """Return a live conversation or raise 404."""
        return await self._require_conversation(conversation_id)

    async def list_user_conversations(
        self, *, user_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> Page[AIConversation]:
        """Paginate a user's conversations, most recently active first."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        return await self._conversations.get_history(user_id, page=page, limit=limit)

    async def _append_first_message(
        self, conversation: AIConversation, content: str
    ) -> ChatMessage:
        """Seed a conversation with its first user message and bump counters."""
        message = await self._messages.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
            status=MessageStatus.COMPLETED,
        )
        await self._conversations.update(
            conversation,
            message_count=conversation.message_count + 1,
            last_message_at=utc_now(),
        )
        return message

    async def _require_conversation(
        self, conversation_id: uuid.UUID
    ) -> AIConversation:
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError(message="Conversation not found")
        return conversation

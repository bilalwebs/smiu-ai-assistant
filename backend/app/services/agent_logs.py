"""``agent_logs`` service (BACKEND_ARCHITECTURE.md §11; AI_ARCHITECTURE.md §11.2, §30.1).

Append-only agent routing/execution log. Persists the routing signal, retrieval
and grounding evidence, model/token/latency usage, and error/retry/fallback
outcomes for every run. Rows are never edited (DATABASE_DESIGN.md §24 note).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentKey, AgentLog, AgentRunStatus
from app.repositories import (
    AgentLogRepository,
    ChatMessageRepository,
    ConversationRepository,
    UserRepository,
)
from app.services.base import BaseService
from app.services.exceptions import NotFoundError, ValidationError


class AgentLogService(BaseService):
    """Append-only agent-log operations for :class:`app.models.agent_logs.AgentLog`."""

    def __init__(
        self,
        session: AsyncSession,
        logs: AgentLogRepository | None = None,
        users: UserRepository | None = None,
        conversations: ConversationRepository | None = None,
        messages: ChatMessageRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._logs = logs or AgentLogRepository(session)
        self._users = users or UserRepository(session)
        self._conversations = conversations or ConversationRepository(session)
        self._messages = messages or ChatMessageRepository(session)

    async def create_log(
        self,
        *,
        run_status: AgentRunStatus,
        user_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        message_id: uuid.UUID | None = None,
        agent_key: AgentKey | None = None,
        intent: str | None = None,
        confidence: float | None = None,
        model: str | None = None,
        token_usage: dict[str, Any] | None = None,
        latency_ms: int | None = None,
        error_code: str | None = None,
        retry_count: int | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> AgentLog:
        """Record one agent run (routing + outcome) (AI_ARCHITECTURE.md §11.2)."""
        run_status = self._validate_enum(
            run_status, AgentRunStatus, field="run_status"
        )
        agent_key = (
            self._validate_enum(agent_key, AgentKey, field="agent_key")
            if agent_key is not None
            else None
        )
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValidationError(
                message="confidence must be between 0 and 1",
                details=[{"field": "confidence", "reason": "out of range"}],
            )
        if latency_ms is not None and latency_ms < 0:
            raise ValidationError(
                message="latency_ms must not be negative",
                details=[{"field": "latency_ms", "reason": "negative"}],
            )
        if retry_count is not None and retry_count < 0:
            raise ValidationError(
                message="retry_count must not be negative",
                details=[{"field": "retry_count", "reason": "negative"}],
            )
        await self._validate_references(user_id, conversation_id, message_id)
        values: dict[str, Any] = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "agent_key": agent_key,
            "intent": intent,
            "run_status": run_status,
            "confidence": confidence,
            "model": model,
            "token_usage": token_usage,
            "latency_ms": latency_ms,
            "error_code": error_code,
            "retry_count": retry_count,
        }
        if metadata_ is not None:
            values["metadata_"] = metadata_
        return await self._logs.create(**values)

    async def list_by_conversation(
        self,
        *,
        conversation_id: uuid.UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AgentLog]:
        """List a conversation's agent runs, newest first."""
        if await self._conversations.get_by_id(conversation_id) is None:
            raise NotFoundError(message="Conversation not found")
        return await self._logs.list_by_conversation(
            conversation_id, limit=limit, offset=offset
        )

    async def _validate_references(
        self,
        user_id: uuid.UUID | None,
        conversation_id: uuid.UUID | None,
        message_id: uuid.UUID | None,
    ) -> None:
        """Raise 404 when a referenced entity does not exist."""
        if user_id is not None and await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        if (
            conversation_id is not None
            and await self._conversations.get_by_id(conversation_id) is None
        ):
            raise NotFoundError(message="Conversation not found")
        if message_id is not None and await self._messages.get_by_id(message_id) is None:
            raise NotFoundError(message="Message not found")

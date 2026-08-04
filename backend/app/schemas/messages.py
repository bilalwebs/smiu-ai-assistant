"""Chat message schemas (API_SPECIFICATION.md §20).

Purpose:
    Define the message send/history payloads. Message lifecycle states follow
    ui-ux-design.md §36; persistence lives in ``chat_history``
    (DATABASE_DESIGN.md §16).
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.models import AgentKey, MessageRole, MessageStatus
from app.schemas.base import ApiModel, UtcDateTime


class MessageSend(BaseModel):
    """Payload for ``POST /conversations/{id}/messages``.

    The current phase persists the user message; AI reply generation plugs in
    behind the agentic boundary later (AI_ARCHITECTURE.md §2).
    """

    content: str = Field(min_length=1)
    content_format: str = Field(default="markdown", max_length=20)
    parent_message_id: uuid.UUID | None = None


class MessageRead(ApiModel):
    """A single chat message (DATABASE_DESIGN.md §16)."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    parent_message_id: uuid.UUID | None = None
    role: MessageRole
    agent_key: AgentKey | None = None
    content: str
    content_format: str
    status: MessageStatus
    model: str | None = None
    token_usage: dict[str, Any] | None = None
    latency_ms: int | None = None
    error_code: str | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime

"""Conversation schemas (API_SPECIFICATION.md §20, §22).

Purpose:
    Define the AI chat-session payloads: creation, metadata updates, and the
    read representation (DATABASE_DESIGN.md §15).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models import AgentKey, ConversationStatus
from app.schemas.base import ApiModel, UtcDateTime


class ConversationCreate(BaseModel):
    """Payload for ``POST /conversations`` (§20)."""

    department_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=200)
    summary: str | None = None
    current_agent: AgentKey | None = None
    first_message: str | None = Field(default=None, min_length=1)


class ConversationUpdate(BaseModel):
    """Editable conversation metadata for ``PATCH /conversations/{id}`` (§22)."""

    title: str | None = Field(default=None, max_length=200)
    summary: str | None = None
    current_agent: AgentKey | None = None


class ConversationRead(ApiModel):
    """Chat-session representation (DATABASE_DESIGN.md §15)."""

    id: uuid.UUID
    user_id: uuid.UUID
    department_id: uuid.UUID | None = None
    title: str | None = None
    summary: str | None = None
    status: ConversationStatus
    current_agent: AgentKey | None = None
    message_count: int
    total_tokens: int
    started_at: UtcDateTime
    last_message_at: UtcDateTime | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime

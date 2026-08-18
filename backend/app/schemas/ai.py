"""AI schemas (API_SPECIFICATION.md §21).

Purpose:
    Define the AI-adjacent payloads the current phase exposes: the ``/ai/chat``
    agentic envelope (request/response with the active agent, handoff metadata,
    and citations), citation sources per message, and user feedback on AI
    messages.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models import (
    AgentKey,
    FeedbackSentiment,
    FeedbackStatus,
    FeedbackType,
    SourceType,
)
from app.schemas.base import ApiModel, UtcDateTime


class ChatRequest(BaseModel):
    """Payload for ``POST /ai/chat`` (API_SPECIFICATION.md §21.1).

    ``conversation_id`` is optional: omit it to start a new conversation, or
    pass it to continue an existing (owned, active) one. ``department_id``
    records the optional origin (department page) of a new conversation.
    ``document_ids`` references previously uploaded documents whose extracted
    text should be included as context for this turn.
    """

    conversation_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=4000)
    department_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] = Field(default_factory=list)


class HandoffRead(ApiModel):
    """Agent handoff metadata for the response envelope (§21.2, §24.4).

    ``previous_agent`` is the agent the conversation was with before this turn
    (the Coordinator for the first specialist route); ``routed_to`` is the
    newly active specialist. ``reason`` mirrors the routing decision and never
    contains secrets or raw provider errors.
    """

    routed_to: AgentKey
    previous_agent: AgentKey
    reason: str | None = None


class ChatCitationRead(ApiModel):
    """A citation returned inline with the AI response (§21.4).

    ``knowledge_document_id``/``knowledge_chunk_id`` are the persisted links
    when the source resolves against the knowledge base; the snapshot fields
    (title, url/path, category, snippet, relevance score) always travel with
    the citation.
    """

    source_title: str
    source_url: str | None = None
    category: str | None = None
    snippet: str | None = None
    relevance_score: float | None = None
    knowledge_document_id: uuid.UUID | None = None
    knowledge_chunk_id: uuid.UUID | None = None


class ChatResponse(ApiModel):
    """Envelope returned by ``POST /ai/chat`` (§21.2-21.4).

    Carries the grounded ``answer``, the active agent, handoff metadata, and
    the citation list. ``status`` mirrors the workflow turn status
    (``completed``/``clarifying``/``fallback``/``error``/``stopped``) so the
    client can distinguish a routed answer from a clarifying turn. The message
    ids let the client link feedback and fetch per-message sources via
    ``GET /ai/sources/{message_id}`` (§21.4).
    """

    conversation_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID
    answer: str
    status: str
    active_agent: AgentKey | None = None
    handoff: HandoffRead | None = None
    citations: list[ChatCitationRead] = Field(default_factory=list)


class AISourceRead(ApiModel):
    """A citation linking an assistant message to a knowledge source (§22)."""

    id: uuid.UUID
    message_id: uuid.UUID
    knowledge_document_id: uuid.UUID | None = None
    knowledge_chunk_id: uuid.UUID | None = None
    source_type: SourceType
    source_title: str
    source_url: str | None = None
    category: str | None = None
    relevance_score: float | None = None
    snippet: str | None = None
    retrieved_at: UtcDateTime
    created_at: UtcDateTime


class FeedbackSubmit(BaseModel):
    """Payload for ``POST /ai/feedback`` (API_SPECIFICATION.md §21.5)."""

    message_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    feedback_type: FeedbackType = FeedbackType.RATING
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None
    sentiment: FeedbackSentiment | None = None


class FeedbackStatusUpdate(BaseModel):
    """Payload for triage status transitions on feedback (§23)."""

    status: FeedbackStatus
    resolution_notes: str | None = None


class FeedbackRead(ApiModel):
    """Rating / comment / flag on an AI message (DATABASE_DESIGN.md §23)."""

    id: uuid.UUID
    user_id: uuid.UUID
    message_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    feedback_type: FeedbackType
    rating: int | None = None
    comment: str | None = None
    sentiment: FeedbackSentiment | None = None
    status: FeedbackStatus
    resolution_notes: str | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime

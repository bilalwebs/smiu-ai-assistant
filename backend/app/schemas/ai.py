"""AI schemas (API_SPECIFICATION.md §21).

Purpose:
    Define the AI-adjacent payloads that the current phase exposes: citation
    sources per message and user feedback on AI messages. The ``/ai/chat``
    agentic boundary remains out of scope until the LLM layer lands.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models import (
    FeedbackSentiment,
    FeedbackStatus,
    FeedbackType,
    SourceType,
)
from app.schemas.base import ApiModel, UtcDateTime


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

"""Shared workflow state types for the AI service.

Purpose:
    The typed Pydantic graph-state foundation consumed by the LangGraph
    workflow and every agent (AI_ARCHITECTURE.md §10.2, §12). The state object
    is the single source of truth during a run; it is written to persistent
    storage only at defined checkpoints (AI_ARCHITECTURE.md §12.1).

    This module contains type definitions only — no graph nodes, edges,
    reducers, agents, retrieval, or LLM calls.

Fields (AI_ARCHITECTURE.md §10.2):
    ``user_query``      current user turn
    ``conversation_id`` owning conversation (UUID)
    ``user_context``    authenticated user info, role, department
    ``current_agent``   active agent entering the run (last handoff, §24)
    ``message_history`` recent turns (short-term memory window)
    ``routing_signal``  intent, selected agent, confidence
    ``handoff``         handoff metadata for the response envelope (§24.4)
    ``retrieved_context`` retrieved chunks + metadata
    ``agent_output``    specialist answer, citations, status
    ``metadata``        provider data, timings, correlation ID
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IntentCategory(StrEnum):
    """Intent labels produced by the Coordinator (AI_ARCHITECTURE.md §4.1)."""

    ADMISSION = "admission"
    EXAMINATION = "examination"
    FAQ = "faq"
    GENERAL = "general"
    OUT_OF_SCOPE = "out_of_scope"


class AgentKey(StrEnum):
    """Registered Phase 1 agents (AI_ARCHITECTURE.md §3.2)."""

    COORDINATOR = "coordinator"
    ADMISSION = "admission"
    EXAMINATION = "examination"
    FAQ = "faq"


class MessageRole(StrEnum):
    """Message roles persisted in ``chat_history`` (DATABASE_DESIGN.md §32.2)."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class WorkflowStatus(StrEnum):
    """Turn completion status (AI_ARCHITECTURE.md §11.6 termination conditions).

    ``completed``   response envelope built and persisted (normal termination)
    ``clarifying``  ambiguous intent; clarifying turn returned (§9.5, §11.5)
    ``fallback``    fallback routing/response after a failure (§4.6, §23.2)
    ``error``       run ended on a caught failure with a friendly retry signal (§23)
    ``stopped``     user stopped streaming; partial response retained (§11.6)
    """

    COMPLETED = "completed"
    CLARIFYING = "clarifying"
    FALLBACK = "fallback"
    ERROR = "error"
    STOPPED = "stopped"


class UserRole(StrEnum):
    """Authenticated user role (AI_ARCHITECTURE.md §10.3).

    Values mirror the backend ``user_role`` domain (BACKEND_ARCHITECTURE.md §10)
    while keeping the AI service decoupled from backend models.
    """

    STUDENT = "student"
    ADMIN = "admin"
    FACULTY = "faculty"


class ChatTurn(BaseModel):
    """A single message within the short-term memory window (§10.2, §21.2)."""

    role: MessageRole
    content: str


class UserContext(BaseModel):
    """Authenticated user context injected into the workflow (§10.2-10.3)."""

    user_id: uuid.UUID
    user_role: UserRole
    department: str | None = None
    locale: str = "en"


class RoutingSignal(BaseModel):
    """Coordinator routing decision (§9.1).

    ``secondary_intents`` notes additional topics in multi-topic input (§9.1);
    the primary intent is selected and routed. ``reason`` explains the decision
    for traceability and clarifying/fallback turns (§9.4, §9.5); it never
    contains secrets or raw provider errors.
    """

    intent: IntentCategory
    selected_agent: AgentKey
    confidence: float = Field(ge=0.0, le=1.0)
    secondary_intents: list[IntentCategory] = Field(default_factory=list)
    reason: str | None = None


class RetrievedChunk(BaseModel):
    """A retrieved knowledge chunk plus source metadata (§16, §19.1).

    ``score`` is the raw similarity score from the index (§16.3); it is not
    normalized to the ``ai_sources.relevance_score`` range.
    """

    chunk_id: str
    document_id: uuid.UUID | None = None
    title: str
    category: str
    snippet: str
    score: float


class Citation(BaseModel):
    """A citation attached to an assistant answer (§19, DATABASE_DESIGN.md §22).

    ``relevance_score`` is constrained to 0..1 to match the
    ``ai_sources_score_check`` database constraint (DATABASE_DESIGN.md §32.6).
    """

    title: str
    category: str
    snippet: str
    url: str | None = None
    document_id: uuid.UUID | None = None
    chunk_id: str | None = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class Handoff(BaseModel):
    """Agent handoff metadata for the response envelope (§24.3-24.4).

    Recorded when the Coordinator routes a turn to a specialist, or when a
    follow-up re-routes to a different specialist (§24.2). ``previous_agent``
    is the agent the conversation was with before this handoff (the Coordinator
    for the first specialist route); ``routed_to`` is the newly active agent.
    ``reason`` mirrors the routing decision for traceability and never contains
    secrets or raw provider errors (§24.4, §9.4).
    """

    routed_to: AgentKey
    previous_agent: AgentKey
    reason: str | None = None


class AgentOutput(BaseModel):
    """Specialist agent result written back to graph state (§10.2, §3.3)."""

    answer: str = ""
    citations: list[Citation] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.COMPLETED


class WorkflowState(BaseModel):
    """Typed graph state — single source of truth during a run (§10.2, §12).

    Only the fields defined by the architecture are present. Nodes populate
    fields as the run progresses; ``metadata`` carries auxiliary data such as
    model name/version, token usage, latency, provider call IDs, and the
    correlation ID (§10.4).
    """

    user_query: str
    conversation_id: uuid.UUID | None = None
    user_context: UserContext | None = None
    current_agent: AgentKey | None = None
    message_history: list[ChatTurn] = Field(default_factory=list)
    routing_signal: RoutingSignal | None = None
    handoff: Handoff | None = None
    retrieved_context: list[RetrievedChunk] = Field(default_factory=list)
    agent_output: AgentOutput | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    user_document_texts: list[str] = Field(default_factory=list)

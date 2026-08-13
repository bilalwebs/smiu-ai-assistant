"""AI workflow state tests (AI_ARCHITECTURE.md §10.2, §12).

Verify that:
    - the typed state object constructs with valid values,
    - defaults are safe and independent per instance,
    - invalid values are rejected where the architecture requires validation
      (confidence 0..1; ``ai_sources`` relevance_score 0..1 per the
      ``ai_sources_score_check`` constraint in DATABASE_DESIGN.md §32.6).
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from ai.core.state import (
    AgentKey,
    AgentOutput,
    ChatTurn,
    Citation,
    IntentCategory,
    MessageRole,
    RetrievedChunk,
    RoutingSignal,
    UserContext,
    UserRole,
    WorkflowState,
    WorkflowStatus,
)


def test_workflow_state_constructible_with_minimal_input() -> None:
    state = WorkflowState(user_query="When is the mid-term exam?")
    assert state.user_query == "When is the mid-term exam?"
    assert state.conversation_id is None
    assert state.user_context is None
    assert state.message_history == []
    assert state.routing_signal is None
    assert state.retrieved_context == []
    assert state.agent_output is None
    assert state.metadata == {}


def test_full_workflow_state_round_trip() -> None:
    conversation_id = uuid.uuid4()
    user_context = UserContext(
        user_id=uuid.uuid4(),
        user_role=UserRole.STUDENT,
        department="Computer Science",
    )
    routing_signal = RoutingSignal(
        intent=IntentCategory.EXAMINATION,
        selected_agent=AgentKey.EXAMINATION,
        confidence=0.95,
    )
    chunk = RetrievedChunk(
        chunk_id="chunk-1",
        title="Mid-Term Date Sheet",
        category="examination",
        snippet="Mid-term exams begin on...",
        score=0.87,
    )
    output = AgentOutput(
        answer="Mid-term exams begin on...",
        citations=[Citation(title="Mid-Term Date Sheet", category="examination", snippet="...")],
        status=WorkflowStatus.COMPLETED,
    )
    state = WorkflowState(
        user_query="When is the mid-term exam?",
        conversation_id=conversation_id,
        user_context=user_context,
        message_history=[ChatTurn(role=MessageRole.USER, content="When is the mid-term exam?")],
        routing_signal=routing_signal,
        retrieved_context=[chunk],
        agent_output=output,
        metadata={"correlation_id": "corr-1", "model": "gemini-2.5-flash"},
    )
    assert state.conversation_id == conversation_id
    assert state.routing_signal is not None
    assert state.routing_signal.selected_agent is AgentKey.EXAMINATION
    assert state.agent_output is not None
    assert state.agent_output.citations[0].title == "Mid-Term Date Sheet"
    assert state.metadata["correlation_id"] == "corr-1"


def test_state_defaults_are_independent_per_instance() -> None:
    first = WorkflowState(user_query="a")
    second = WorkflowState(user_query="b")
    first.message_history.append(ChatTurn(role=MessageRole.USER, content="a"))
    assert second.message_history == []


def test_routing_signal_confidence_validated() -> None:
    with pytest.raises(ValidationError):
        RoutingSignal(intent="examination", selected_agent="examination", confidence=1.2)
    with pytest.raises(ValidationError):
        RoutingSignal(intent="examination", selected_agent="examination", confidence=-0.1)
    signal = RoutingSignal(intent="examination", selected_agent="examination", confidence=0.8)
    assert signal.intent is IntentCategory.EXAMINATION
    assert signal.selected_agent is AgentKey.EXAMINATION


def test_routing_signal_reason_round_trips() -> None:
    signal = RoutingSignal(
        intent="admission",
        selected_agent="admission",
        confidence=0.9,
        reason="clear match",
    )
    assert signal.reason == "clear match"
    assert (
        RoutingSignal(intent="admission", selected_agent="admission", confidence=0.9).reason
        is None
    )


def test_citation_relevance_score_validated_like_ai_sources() -> None:
    with pytest.raises(ValidationError):
        Citation(title="t", category="faq", snippet="s", relevance_score=1.5)
    citation = Citation(title="t", category="faq", snippet="s", relevance_score=0.5)
    assert citation.relevance_score == 0.5


def test_user_context_requires_user_id_and_role() -> None:
    with pytest.raises(ValidationError):
        UserContext()
    context = UserContext(user_id=uuid.uuid4(), user_role=UserRole.STUDENT)
    assert context.locale == "en"
    assert context.department is None


def test_metadata_accepts_arbitrary_values() -> None:
    state = WorkflowState(
        user_query="q",
        metadata={"token_usage": {"prompt": 10, "completion": 5}, "provider_call_id": "p-1"},
    )
    assert state.metadata["token_usage"]["completion"] == 5

"""Conversation memory + agent handoff + error recovery tests.

Step 1I scope (AI_ARCHITECTURE.md §21, §22.5, §23, §24; IMPLEMENTATION_PLAN.md
§4 AI tasks 9-10):

- short-term memory: the ``CHAT_HISTORY_LIMIT`` window (default 20, §21.6) is
  enforced when turns are appended and when history is injected into context
  (§21.2, §12.5),
- long-term memory: opt-in overflow summarization via an injected summarizer
  (§21.3); without long-term memory or a summarizer, overflow is dropped safely,
- session memory: rebuilt from persisted history + summary at session start
  (§21.4, §22.5),
- error recovery: memory persistence failures never fail the run (§23.1),
- agent handoff: the route node records the active agent and §24 handoff
  metadata (routed_to / previous_agent / reason) for the response envelope,
  recorded only on an actual agent change (§24.2-24.4).

All tests are deterministic and offline — no external AI/API/network/database
calls. The summarizer and classifier are injected fakes.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from ai.agents.coordinator import create_coordinator
from ai.agents.intent_classifier import IntentResult
from ai.core.state import (
    AgentKey,
    ChatTurn,
    Handoff,
    IntentCategory,
    MessageRole,
    RoutingSignal,
    WorkflowState,
)
from ai.graphs.workflow import _detect_intent_with, _route_with
from ai.memory.manager import ConversationMemoryManager


def _turns(*contents: str) -> list[ChatTurn]:
    return [ChatTurn(role=MessageRole.USER, content=content) for content in contents]


def _summarize(turns: Sequence[ChatTurn]) -> str:
    return "OVERFLOW: " + " | ".join(turn.content for turn in turns)


class RecordingClassifier:
    """Intent classifier spy: records the history it was given (§12.5)."""

    def __init__(self) -> None:
        self.seen_history: list[ChatTurn] | None = None

    def classify(
        self,
        *,
        user_query: str,
        agent_descriptions: str,
        message_history: Sequence[ChatTurn] | None = None,
        user_context: object | None = None,
    ) -> IntentResult:
        self.seen_history = list(message_history) if message_history else []
        return IntentResult(intent=IntentCategory.GENERAL, confidence=0.1)


# --- Short-term memory window (§21.2, §21.6) --------------------------------


def test_window_returns_last_20_turns_by_default() -> None:
    turns = _turns(*(str(i) for i in range(25)))
    memory = ConversationMemoryManager()
    assert memory.window(turns) == turns[-20:]


def test_window_honors_custom_chat_history_limit() -> None:
    turns = _turns(*(str(i) for i in range(25)))
    memory = ConversationMemoryManager(chat_history_limit=3)
    assert memory.window(turns) == turns[-3:]


def test_window_empty_history() -> None:
    assert ConversationMemoryManager().window([]) == []


def test_add_turn_within_window_has_no_overflow() -> None:
    memory = ConversationMemoryManager(chat_history_limit=5)
    window, overflow = memory.add_turn(_turns("0", "1", "2"), role=MessageRole.USER, content="3")
    assert len(window) == 4
    assert overflow == []


def test_add_turn_returns_overflow_beyond_window() -> None:
    memory = ConversationMemoryManager(chat_history_limit=2)
    window, overflow = memory.add_turn(_turns("0", "1", "2"), role=MessageRole.USER, content="3")
    assert window == _turns("2", "3")
    assert overflow == _turns("0", "1")


# --- Commit: short-term + long-term (§21.2, §21.3) --------------------------


def test_commit_short_term_only_drops_overflow() -> None:
    memory = ConversationMemoryManager(chat_history_limit=2)
    result = memory.commit(_turns("0", "1", "2"), role=MessageRole.USER, content="3")
    assert result.history == _turns("2", "3")
    assert result.summary is None


def test_commit_long_term_summarizes_overflow() -> None:
    memory = ConversationMemoryManager(
        chat_history_limit=2,
        long_term_enabled=True,
        summarizer=_summarize,
    )
    result = memory.commit(_turns("0", "1", "2"), role=MessageRole.USER, content="3")
    assert result.history == _turns("2", "3")
    assert result.summary == "OVERFLOW: 0 | 1"


def test_commit_folds_later_overflow_into_existing_summary() -> None:
    memory = ConversationMemoryManager(
        chat_history_limit=2,
        long_term_enabled=True,
        summarizer=_summarize,
    )
    first = memory.commit(_turns("0", "1", "2"), role=MessageRole.USER, content="3")
    second = memory.commit(
        first.history,
        role=MessageRole.USER,
        content="4",
        current_summary=first.summary,
    )
    assert second.history == _turns("3", "4")
    assert second.summary == "OVERFLOW: 0 | 1\nOVERFLOW: 2"


def test_commit_keeps_existing_summary_when_no_overflow() -> None:
    memory = ConversationMemoryManager(
        chat_history_limit=5,
        long_term_enabled=True,
        summarizer=_summarize,
    )
    result = memory.commit(
        _turns("0"),
        role=MessageRole.USER,
        content="1",
        current_summary="prior summary",
    )
    assert result.summary == "prior summary"
    assert result.history == _turns("0", "1")


def test_commit_long_term_without_summarizer_drops_overflow_safely() -> None:
    memory = ConversationMemoryManager(chat_history_limit=2, long_term_enabled=True)
    result = memory.commit(_turns("0", "1", "2"), role=MessageRole.USER, content="3")
    assert result.history == _turns("2", "3")
    assert result.summary is None


def test_chat_history_limit_must_be_positive() -> None:
    with pytest.raises(ValueError):
        ConversationMemoryManager(chat_history_limit=0)


# --- Session memory rebuild (§21.4, §22.5) ----------------------------------


def test_rebuild_reconstructs_window_and_summary() -> None:
    memory = ConversationMemoryManager(chat_history_limit=2)
    persisted = _turns("0", "1", "2", "3", "4")
    session = memory.rebuild(persisted, summary="archived summary")
    assert session.history == _turns("3", "4")
    assert session.summary == "archived summary"
    assert session.history[0].role is MessageRole.USER


def test_rebuild_without_summary() -> None:
    memory = ConversationMemoryManager(chat_history_limit=20)
    session = memory.rebuild(_turns("a", "b"))
    assert session.summary is None
    assert session.history == _turns("a", "b")


# --- Error recovery: memory persistence failure (§23.1) ---------------------


def test_persist_success_returns_true() -> None:
    memory = ConversationMemoryManager()
    written: list[list[ChatTurn]] = []

    def writer(history: Sequence[ChatTurn]) -> object:
        written.append(list(history))
        return None

    turns = _turns("hello")
    assert memory.persist(turns, writer) is True
    assert written == [turns]


def test_persist_failure_returns_false_and_never_raises() -> None:
    memory = ConversationMemoryManager()

    def failing_writer(history: Sequence[ChatTurn]) -> object:
        raise RuntimeError("database unavailable")

    assert memory.persist(_turns("hello"), failing_writer) is False


# --- Agent handoff (§24) -----------------------------------------------------


def test_route_records_first_handoff_from_coordinator() -> None:
    state = WorkflowState(
        user_query="When is the mid-term exam?",
        routing_signal=RoutingSignal(
            intent=IntentCategory.EXAMINATION,
            selected_agent=AgentKey.COORDINATOR,
            confidence=0.9,
        ),
    )
    update = _route_with(create_coordinator(), state)
    assert update["routing_signal"].selected_agent is AgentKey.EXAMINATION
    assert update["current_agent"] is AgentKey.EXAMINATION
    handoff = update["handoff"]
    assert isinstance(handoff, Handoff)
    assert handoff.routed_to is AgentKey.EXAMINATION
    assert handoff.previous_agent is AgentKey.COORDINATOR


def test_route_switch_records_handoff_old_and_new_agent() -> None:
    state = WorkflowState(
        user_query="What are the library hours?",
        current_agent=AgentKey.EXAMINATION,
        routing_signal=RoutingSignal(
            intent=IntentCategory.FAQ,
            selected_agent=AgentKey.COORDINATOR,
            confidence=0.9,
        ),
    )
    update = _route_with(create_coordinator(), state)
    assert update["current_agent"] is AgentKey.FAQ
    handoff = update["handoff"]
    assert isinstance(handoff, Handoff)
    assert handoff.routed_to is AgentKey.FAQ
    assert handoff.previous_agent is AgentKey.EXAMINATION


def test_route_same_agent_does_not_record_new_handoff() -> None:
    state = WorkflowState(
        user_query="Another FAQ question",
        current_agent=AgentKey.FAQ,
        routing_signal=RoutingSignal(
            intent=IntentCategory.FAQ,
            selected_agent=AgentKey.COORDINATOR,
            confidence=0.9,
        ),
    )
    update = _route_with(create_coordinator(), state)
    assert update["current_agent"] is AgentKey.FAQ
    assert "handoff" not in update


def test_route_unresolved_signal_keeps_coordinator_without_handoff() -> None:
    state = WorkflowState(
        user_query="Something ambiguous",
        routing_signal=RoutingSignal(
            intent=IntentCategory.GENERAL,
            selected_agent=AgentKey.COORDINATOR,
            confidence=0.2,
        ),
    )
    assert _route_with(create_coordinator(), state) == {}


def test_handoff_model_round_trips() -> None:
    handoff = Handoff(
        routed_to=AgentKey.EXAMINATION,
        previous_agent=AgentKey.COORDINATOR,
        reason="clear exam intent",
    )
    assert handoff.routed_to is AgentKey.EXAMINATION
    assert handoff.previous_agent is AgentKey.COORDINATOR
    assert handoff.reason == "clear exam intent"
    minimal = Handoff(routed_to=AgentKey.FAQ, previous_agent=AgentKey.COORDINATOR)
    assert minimal.reason is None


def test_workflow_state_handoff_fields_default_to_none() -> None:
    state = WorkflowState(user_query="q")
    assert state.current_agent is None
    assert state.handoff is None


# --- Memory injected into context (§12.5, §21.2) ----------------------------


def test_detect_intent_applies_memory_window_before_classification() -> None:
    classifier = RecordingClassifier()
    coordinator = create_coordinator(classifier=classifier)  # type: ignore[arg-type]
    memory = ConversationMemoryManager(chat_history_limit=1)
    state = WorkflowState(
        user_query="What is the fee deadline?",
        message_history=_turns("0", "1", "2"),
    )
    update = _detect_intent_with(coordinator, state, memory=memory)
    assert "routing_signal" in update
    assert classifier.seen_history == _turns("2")

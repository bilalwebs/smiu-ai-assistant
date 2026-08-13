"""LangGraph clarify-node integration tests (Step 1L, AI_ARCHITECTURE.md §9.4-9.5, §11.3, §11.5).

Scope:
    - ambiguous / low-confidence / unknown / out-of-scope turns route to the
      ``clarify`` node (§11.3 edge, §9.4), never to a specialist,
    - the clarify node returns a grounded, safe, student-facing clarifying turn
      through the ``AgentOutput`` contract with ``WorkflowStatus.CLARIFYING``
      (§4.6, §11.6),
    - no specialist is executed and no LLM/retrieval call happens on the
      clarify path (§9.5 — the Coordinator never guesses),
    - the original ``routing_signal``, ``conversation_id``, ``user_context``,
      ``message_history``, and ``current_agent``/``handoff`` semantics are all
      preserved (§10.2, §24),
    - low-confidence domain intents optionally name the nearest specialist
      without selecting it (§9.4); out-of-scope intents get a scope boundary +
      department referral (§4.6, §9.5).

All tests are deterministic and fully offline: fake retriever, scripted fake
gateway, and the rule-based (or scripted-LLM) Coordinator. No external
AI/API/network/database calls and no real Gemini/OpenAI/Groq clients.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from ai.agents.admission import create_admission_agent
from ai.agents.base import SpecialistAgent
from ai.agents.coordinator import create_coordinator, create_llm_coordinator
from ai.core.config import Settings
from ai.core.state import (
    AgentKey,
    AgentOutput,
    ChatTurn,
    IntentCategory,
    MessageRole,
    RetrievedChunk,
    RoutingSignal,
    UserContext,
    UserRole,
    WorkflowState,
    WorkflowStatus,
)
from ai.gateway.base import LLMGateway, LLMResponse
from ai.graphs.workflow import (
    NODE_CLARIFY,
    _clarify_with,
    _detect_intent_with,
    _route_with,
    build_workflow,
    route_after_detect,
)


def _chunk(chunk_id: str = "c1", *, snippet: str = "Campus information.") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        title="Campus Guide",
        category="faq",
        snippet=snippet,
        score=0.8,
    )


class FakeRetriever:
    """Scripted retriever recording query/categories/top_k (offline)."""

    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self.chunks = chunks or []
        self.calls: list[dict[str, object]] = []

    def retrieve(
        self,
        *,
        query: str,
        categories: Sequence[str] = (),
        top_k: int = 4,
    ) -> list[RetrievedChunk]:
        self.calls.append(
            {"query": query, "categories": tuple(categories), "top_k": top_k}
        )
        return list(self.chunks)


class LoudGateway(LLMGateway):
    """Fails loudly if any provider call is ever attempted (offline proof)."""

    def __init__(self) -> None:
        super().__init__(model="fake-model", max_retries=0)
        self.calls = 0

    def _complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_schema: dict[str, object] | None,
    ) -> LLMResponse:
        self.calls += 1
        raise AssertionError("no provider call may happen during clarification")


class LowConfidenceIntentGateway(LLMGateway):
    """LLM-coordinator gateway that classifies the turn as low-confidence domain."""

    def __init__(self) -> None:
        super().__init__(model="fake-model", max_retries=0)
        self.calls = 0

    def _complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_schema: dict[str, object] | None,
    ) -> LLMResponse:
        self.calls += 1
        payload = (
            '{"intent": "examination", "confidence": 0.4, '
            '"secondary_intents": [], "reason": "low confidence"}'
        )
        return LLMResponse(content=payload, model="recorder")


class RecordingSpecialist(SpecialistAgent):
    """Dependency-injection spy: never touches retrieval or the LLM."""

    AGENT_KEY = AgentKey.FAQ

    def __init__(self) -> None:
        self.seen_queries: list[str] = []
        self.seen_history: list[ChatTurn] = []
        self.seen_context: list[object] = []

    def run(
        self,
        *,
        query: str,
        message_history: Sequence[ChatTurn] = (),
        user_context: UserContext | None = None,
    ) -> AgentOutput:
        self.seen_queries.append(query)
        self.seen_history = list(message_history)
        self.seen_context.append(user_context)
        return AgentOutput(answer="fake answer", status=WorkflowStatus.COMPLETED)


_SETTINGS = Settings(llm_provider="gemini", gemini_api_key="dummy")
_CTX = UserContext(user_id=uuid.uuid4(), user_role=UserRole.STUDENT)
_CONVERSATION_ID = uuid.uuid4()

_AMBIGUOUS_QUERY = "Tell me something about the university"


def _invoke(graph: object, *, user_query: str, **state: object) -> WorkflowState:
    """Run the compiled graph and coerce the returned state dict to WorkflowState."""
    result = graph.invoke({"user_query": user_query, **state})  # type: ignore[attr-defined]
    return WorkflowState.model_validate(result)


# --- Routing to clarify (§9.4, §11.3) ----------------------------------------


def test_ambiguous_intent_routes_to_clarify() -> None:
    coordinator = create_coordinator()
    state = WorkflowState(user_query=_AMBIGUOUS_QUERY)
    pre = state.model_copy(update=_detect_intent_with(coordinator, state))
    routed = pre.model_copy(update=_route_with(coordinator, pre))
    assert routed.routing_signal is not None
    assert routed.routing_signal.selected_agent is AgentKey.COORDINATOR
    assert route_after_detect(routed) == NODE_CLARIFY


def test_low_confidence_intent_routes_to_clarify() -> None:
    gateway = LowConfidenceIntentGateway()
    coordinator = create_llm_coordinator(settings=_SETTINGS, gateway=gateway)
    state = WorkflowState(user_query="When is the mid-term exam?")
    pre = state.model_copy(update=_detect_intent_with(coordinator, state))
    routed = pre.model_copy(update=_route_with(coordinator, pre))
    assert routed.routing_signal is not None
    assert routed.routing_signal.intent is IntentCategory.EXAMINATION
    assert routed.routing_signal.confidence < 0.6
    assert route_after_detect(routed) == NODE_CLARIFY


# --- Clarifying turn through the AgentOutput contract (§4.6, §11.6) ----------


def test_clarify_produces_clarifying_agent_output() -> None:
    graph = build_workflow()
    result = _invoke(graph, user_query=_AMBIGUOUS_QUERY)
    assert result.agent_output is not None
    assert result.agent_output.status is WorkflowStatus.CLARIFYING
    assert result.agent_output.answer
    assert result.agent_output.citations == []


def test_clarification_response_is_safe_and_student_facing() -> None:
    graph = build_workflow()
    result = _invoke(graph, user_query=_AMBIGUOUS_QUERY)
    assert result.agent_output is not None
    answer = result.agent_output.answer
    assert "I can help you with" in answer
    assert "Admission Agent" in answer
    assert "Examination Agent" in answer
    assert "FAQ Agent" in answer
    lowered = answer.lower()
    for internal in (
        "routing_signal",
        "confidence",
        "reason",
        "notimplementederror",
        "coordinator",
        "gemini",
        "system prompt",
    ):
        assert internal not in lowered
    assert result.agent_output.citations == []


def test_missing_routing_signal_handled_safely() -> None:
    coordinator = create_coordinator()
    state = WorkflowState(user_query="Who are you?")
    assert route_after_detect(state) == NODE_CLARIFY
    update = _clarify_with(coordinator, state)
    output = state.model_copy(update=update).agent_output
    assert output is not None
    assert output.status is WorkflowStatus.CLARIFYING
    assert output.answer
    assert "Admission Agent" in output.answer


# --- No specialist / no LLM / no retrieval on the clarify path (§9.5) --------


def test_clarify_never_runs_specialists_or_llm() -> None:
    loud = LoudGateway()
    retriever = FakeRetriever(chunks=[_chunk()])
    admission = create_admission_agent(
        settings=_SETTINGS, retriever=retriever, gateway=loud
    )
    graph = build_workflow(specialists={AgentKey.ADMISSION: admission})
    result = _invoke(graph, user_query=_AMBIGUOUS_QUERY)
    assert result.agent_output is not None
    assert result.agent_output.status is WorkflowStatus.CLARIFYING
    assert loud.calls == 0
    assert retriever.calls == []


def test_injected_specialists_are_never_executed_on_clarify() -> None:
    admission = RecordingSpecialist()
    examination = RecordingSpecialist()
    faq = RecordingSpecialist()
    graph = build_workflow(
        specialists={
            AgentKey.ADMISSION: admission,
            AgentKey.EXAMINATION: examination,
            AgentKey.FAQ: faq,
        }
    )
    result = _invoke(graph, user_query=_AMBIGUOUS_QUERY)
    assert result.agent_output is not None
    assert result.agent_output.status is WorkflowStatus.CLARIFYING
    assert admission.seen_queries == []
    assert examination.seen_queries == []
    assert faq.seen_queries == []


def test_out_of_scope_query_gets_scope_boundary() -> None:
    loud = LoudGateway()
    retriever = FakeRetriever(chunks=[_chunk()])
    admission = create_admission_agent(
        settings=_SETTINGS, retriever=retriever, gateway=loud
    )
    graph = build_workflow(specialists={AgentKey.ADMISSION: admission})
    result = _invoke(graph, user_query="Can you hack a university server?")
    assert result.agent_output is not None
    assert result.agent_output.status is WorkflowStatus.CLARIFYING
    assert "outside what I can assist with" in result.agent_output.answer
    assert loud.calls == 0
    assert retriever.calls == []


# --- State preservation (§10.2, §24) -----------------------------------------


def test_clarify_updates_only_agent_output() -> None:
    coordinator = create_coordinator()
    history = [ChatTurn(role=MessageRole.USER, content="previous turn")]
    signal = RoutingSignal(
        intent=IntentCategory.GENERAL,
        selected_agent=AgentKey.COORDINATOR,
        confidence=0.2,
        reason="no domain keyword matched",
    )
    state = WorkflowState(
        user_query="Who are you?",
        conversation_id=_CONVERSATION_ID,
        user_context=_CTX,
        current_agent=AgentKey.FAQ,
        message_history=history,
        routing_signal=signal,
    )
    update = _clarify_with(coordinator, state)
    assert set(update) == {"agent_output"}
    merged = state.model_copy(update=update)
    assert merged.agent_output is not None
    assert merged.agent_output.status is WorkflowStatus.CLARIFYING
    assert merged.routing_signal == signal
    assert merged.conversation_id == _CONVERSATION_ID
    assert merged.user_context == _CTX
    assert merged.current_agent is AgentKey.FAQ
    assert merged.handoff is None
    assert merged.message_history == history


def test_routing_signal_preserved_after_clarify() -> None:
    graph = build_workflow()
    result = _invoke(graph, user_query=_AMBIGUOUS_QUERY)
    assert result.routing_signal is not None
    assert result.routing_signal.selected_agent is AgentKey.COORDINATOR
    assert result.routing_signal.intent is IntentCategory.GENERAL
    assert result.routing_signal.confidence == 0.2


def test_conversation_id_preserved_after_clarify() -> None:
    graph = build_workflow()
    result = _invoke(graph, user_query=_AMBIGUOUS_QUERY, conversation_id=_CONVERSATION_ID)
    assert result.conversation_id == _CONVERSATION_ID


def test_user_context_preserved_after_clarify() -> None:
    graph = build_workflow()
    result = _invoke(graph, user_query=_AMBIGUOUS_QUERY, user_context=_CTX)
    assert result.user_context == _CTX


def test_message_history_preserved_after_clarify() -> None:
    graph = build_workflow()
    history = [ChatTurn(role=MessageRole.USER, content="previous turn")]
    result = _invoke(graph, user_query=_AMBIGUOUS_QUERY, message_history=history)
    assert result.message_history == history


def test_current_agent_and_handoff_semantics_preserved_after_clarify() -> None:
    graph = build_workflow()
    result = _invoke(graph, user_query=_AMBIGUOUS_QUERY, current_agent=AgentKey.FAQ)
    assert result.current_agent is AgentKey.FAQ
    assert result.handoff is None


# --- Deterministic, offline, injection-friendly (§35, TESTING_STRATEGY §23.2) --


def test_injected_llm_coordinator_clarifies_offline() -> None:
    gateway = LowConfidenceIntentGateway()
    coordinator = create_llm_coordinator(settings=_SETTINGS, gateway=gateway)
    graph = build_workflow(coordinator=coordinator)
    result = _invoke(graph, user_query="When is the mid-term exam?")
    assert result.agent_output is not None
    assert result.agent_output.status is WorkflowStatus.CLARIFYING
    assert gateway.calls == 1


def test_low_confidence_domain_offers_nearest_specialist() -> None:
    gateway = LowConfidenceIntentGateway()
    coordinator = create_llm_coordinator(settings=_SETTINGS, gateway=gateway)
    graph = build_workflow(coordinator=coordinator)
    result = _invoke(graph, user_query="When is the mid-term exam?")
    assert result.agent_output is not None
    assert result.agent_output.status is WorkflowStatus.CLARIFYING
    assert "Examination Agent" in result.agent_output.answer
    assert result.current_agent is None
    assert result.handoff is None
    assert gateway.calls == 1


def test_clarify_is_deterministic_without_prompts_or_gateway() -> None:
    coordinator = create_coordinator()
    signal = RoutingSignal(
        intent=IntentCategory.GENERAL,
        selected_agent=AgentKey.COORDINATOR,
        confidence=0.2,
    )
    first = coordinator.clarify(signal)
    second = coordinator.clarify(signal)
    assert first == second
    assert first
    assert "Admission Agent" in first
    assert coordinator.clarify(None)

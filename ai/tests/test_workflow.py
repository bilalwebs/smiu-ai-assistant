"""LangGraph workflow tests (AI_ARCHITECTURE.md §11-12).

Step 1K scope:
    - structural verification is unchanged (9 §11.2/§11.3 nodes and edges),
    - ``detect_intent`` and ``route`` are implemented and Coordinator-backed,
    - the router edge decision follows §11.3 with §9.4 low-confidence/unknown
      semantics (tentative Coordinator -> clarify, resolved specialist ->
      retrieve),
    - the specialist-phase wiring is covered by ``test_workflow_specialists.py``.

Step 1L scope:
    - the ``clarify`` node is implemented and produces a grounded clarifying
      ``AgentOutput`` with ``WorkflowStatus.CLARIFYING`` (§9.4-9.5, §11.3,
      §11.5) — focused behavioral coverage lives in
      ``test_workflow_clarify.py``.

No test asserts that real agents, RAG, or LLM generation work.
"""

from __future__ import annotations

from ai.agents.coordinator import create_coordinator, create_llm_coordinator
from ai.core.config import Settings
from ai.core.state import AgentKey, IntentCategory, RoutingSignal, WorkflowState, WorkflowStatus
from ai.gateway.base import LLMGateway, LLMResponse
from ai.graphs.workflow import (
    NODE_AGGREGATE_RESPONSE,
    NODE_ASSEMBLE_CITATIONS,
    NODE_BUILD_CONTEXT,
    NODE_CLARIFY,
    NODE_DETECT_INTENT,
    NODE_GENERATE,
    NODE_PERSIST,
    NODE_RETRIEVE,
    NODE_ROUTE,
    _clarify_with,
    _detect_intent_with,
    _route_with,
    build_workflow,
    detect_intent,
    route,
    route_after_detect,
)

EXPECTED_NODES = {
    NODE_DETECT_INTENT,
    NODE_ROUTE,
    NODE_CLARIFY,
    NODE_RETRIEVE,
    NODE_BUILD_CONTEXT,
    NODE_GENERATE,
    NODE_ASSEMBLE_CITATIONS,
    NODE_AGGREGATE_RESPONSE,
    NODE_PERSIST,
}

# §11.3 edges: START -> detect_intent -> route (conditional) -> specialist
# phase; clarify is the §11.5 clarification loop exit. Each run terminates at
# END through persist or clarify (§11.4, §11.6).
EXPECTED_EDGES = {
    ("__start__", NODE_DETECT_INTENT),
    (NODE_DETECT_INTENT, NODE_ROUTE),
    (NODE_ROUTE, NODE_RETRIEVE),
    (NODE_ROUTE, NODE_CLARIFY),
    (NODE_RETRIEVE, NODE_BUILD_CONTEXT),
    (NODE_BUILD_CONTEXT, NODE_GENERATE),
    (NODE_GENERATE, NODE_ASSEMBLE_CITATIONS),
    (NODE_ASSEMBLE_CITATIONS, NODE_AGGREGATE_RESPONSE),
    (NODE_AGGREGATE_RESPONSE, NODE_PERSIST),
    (NODE_PERSIST, "__end__"),
    (NODE_CLARIFY, "__end__"),
}


def test_workflow_module_imports() -> None:
    assert callable(build_workflow)
    assert callable(route_after_detect)
    assert callable(detect_intent)
    assert callable(route)


def test_workflow_compiles_without_external_services() -> None:
    graph = build_workflow()
    assert graph is not None


def test_expected_nodes_exist() -> None:
    graph = build_workflow()
    node_names = set(graph.get_graph().nodes)
    assert EXPECTED_NODES.issubset(node_names)


def test_expected_edges_exist() -> None:
    graph = build_workflow()
    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}
    assert EXPECTED_EDGES.issubset(edges)


def test_graph_terminates_only_via_persist_or_clarify() -> None:
    graph = build_workflow()
    node_names = set(graph.get_graph().nodes)
    terminal_edges = {
        (edge.source, edge.target)
        for edge in graph.get_graph().edges
        if edge.target == "__end__"
    }
    assert terminal_edges == {(NODE_PERSIST, "__end__"), (NODE_CLARIFY, "__end__")}
    assert NODE_PERSIST in node_names
    assert NODE_CLARIFY in node_names


# --- Router edge decision (AI_ARCHITECTURE.md §11.3) -------------------------


def test_router_routes_resolved_signal_to_specialist() -> None:
    state = WorkflowState(
        user_query="When is the mid-term exam?",
        routing_signal=RoutingSignal(
            intent="examination",
            selected_agent="examination",
            confidence=0.9,
        ),
    )
    assert route_after_detect(state) == NODE_RETRIEVE


def test_router_routes_missing_signal_to_clarify() -> None:
    state = WorkflowState(user_query="What is the university about?")
    assert route_after_detect(state) == NODE_CLARIFY


def test_router_routes_tentative_coordinator_to_clarify() -> None:
    state = WorkflowState(
        user_query="Something ambiguous",
        routing_signal=RoutingSignal(
            intent=IntentCategory.GENERAL,
            selected_agent=AgentKey.COORDINATOR,
            confidence=0.2,
        ),
    )
    assert route_after_detect(state) == NODE_CLARIFY


# --- Implemented nodes (Step 1D) --------------------------------------------


def test_detect_intent_node_returns_typed_signal() -> None:
    state = WorkflowState(user_query="When is the mid-term exam?")
    update = detect_intent(state)
    assert "routing_signal" in update
    signal = state.model_copy(update=update).routing_signal
    assert signal is not None
    assert signal.intent is IntentCategory.EXAMINATION
    assert signal.selected_agent is AgentKey.COORDINATOR


def test_route_node_resolves_specialist() -> None:
    state = WorkflowState(user_query="When is the mid-term exam?")
    state = state.model_copy(update=detect_intent(state))
    state = state.model_copy(update=route(state))
    assert state.routing_signal is not None
    assert state.routing_signal.selected_agent is AgentKey.EXAMINATION


def test_route_node_keeps_tentative_coordinator_when_unresolved() -> None:
    state = WorkflowState(user_query="Tell me something about the university")
    state = state.model_copy(update=detect_intent(state))
    state = state.model_copy(update=route(state))
    assert state.routing_signal is not None
    assert state.routing_signal.selected_agent is AgentKey.COORDINATOR
    assert route_after_detect(state) == NODE_CLARIFY


def test_workflow_detect_intent_route_integration() -> None:
    state = WorkflowState(user_query="When is the mid-term exam?")
    state = state.model_copy(update=detect_intent(state))
    state = state.model_copy(update=route(state))
    assert state.routing_signal is not None
    assert state.routing_signal.selected_agent is AgentKey.EXAMINATION
    assert route_after_detect(state) == NODE_RETRIEVE


def test_build_workflow_uses_injected_coordinator() -> None:
    class RecordingGateway(LLMGateway):
        def __init__(self) -> None:
            super().__init__(model="fake", max_retries=0)

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
            payload = (
                '{"intent": "faq", "confidence": 0.9, '
                '"secondary_intents": [], "reason": "llm"}'
            )
            return LLMResponse(content=payload, model="recorder")

    coordinator = create_llm_coordinator(
        settings=Settings(llm_provider="gemini", gemini_api_key="dummy"),
        gateway=RecordingGateway(),
    )
    graph = build_workflow(coordinator=coordinator)
    assert graph is not None
    node_names = set(graph.get_graph().nodes)
    assert EXPECTED_NODES.issubset(node_names)

    state = WorkflowState(user_query="What are the library hours?")
    update = _detect_intent_with(coordinator, state)
    assert update["routing_signal"].intent is IntentCategory.FAQ
    routed = _route_with(coordinator, state.model_copy(update=update))
    assert routed["routing_signal"].selected_agent is AgentKey.FAQ


def test_rule_based_coordinator_injected_into_workflow() -> None:
    coordinator = create_coordinator()
    build_workflow(coordinator=coordinator)
    state = WorkflowState(user_query="When is the mid-term exam?")
    update = _detect_intent_with(coordinator, state)
    assert update["routing_signal"].intent is IntentCategory.EXAMINATION


# --- Clarify node (Step 1L: §9.4-9.5, §11.3, §11.5) --------------------------


def test_clarify_node_produces_clarifying_agent_output() -> None:
    coordinator = create_coordinator()
    state = WorkflowState(
        user_query="Tell me something about the university",
        routing_signal=RoutingSignal(
            intent=IntentCategory.GENERAL,
            selected_agent=AgentKey.COORDINATOR,
            confidence=0.2,
        ),
    )
    update = _clarify_with(coordinator, state)
    assert set(update) == {"agent_output"}
    output = state.model_copy(update=update).agent_output
    assert output is not None
    assert output.status is WorkflowStatus.CLARIFYING
    assert output.answer
    assert output.citations == []


def test_clarify_node_runs_end_to_end() -> None:
    graph = build_workflow()
    result = WorkflowState.model_validate(
        graph.invoke({"user_query": "Tell me something about the university"})
    )
    assert result.agent_output is not None
    assert result.agent_output.status is WorkflowStatus.CLARIFYING
    assert result.agent_output.answer
    assert result.routing_signal is not None
    assert result.routing_signal.selected_agent is AgentKey.COORDINATOR

"""LangGraph workflow foundation (AI_ARCHITECTURE.md §11-12).

Purpose:
    The single LangGraph state machine for the AI service: a Coordinator entry
    (intent detection), a router, the specialist phase (retrieval, context
    building, generation), the response builder, and the persist/exit node.

    Graph shape follows AI_ARCHITECTURE.md §11.1-11.3 exactly:

        START -> detect_intent -> route --(resolved)--> retrieve
                                         `--(unresolved)-> clarify
        retrieve -> build_context -> generate -> assemble_citations
                  -> aggregate_response -> persist -> END
        clarify -> END

    Step 1D scope:
        ``detect_intent`` and ``route`` are implemented and backed by the
        Coordinator agent (AI_ARCHITECTURE.md §4, §9). The Coordinator defaults
        to the deterministic rule-based classifier so the graph still compiles
        and runs without API keys; ``build_workflow(coordinator=...)`` injects
        the LLM-backed Coordinator.

    Step 1K scope:
        The specialist phase is wired to the implemented Phase 1 agents
        (AI_ARCHITECTURE.md §13-20). ``retrieve`` delegates to the specialist
        selected by the router via ``SpecialistAgent.run`` and records the
        ``AgentOutput`` in ``state.agent_output``; ``build_context``,
        ``generate``, ``assemble_citations`` and ``aggregate_response`` are
        honest pass-throughs because the specialist agent runs the full
        pipeline internally (§13.5); ``persist`` appends the exchange to the
        short-term memory window and best-effort persists it through an
        injectable writer (§21, §23.1). Specialists are injected only:
        ``build_workflow(specialists=...)``; the graph never constructs real
        LLM clients or retrievers.

    Step 1L scope:
        ``clarify`` is implemented and no longer a placeholder. It produces a
        deterministic, grounded clarifying turn (AI_ARCHITECTURE.md §4.6,
        §9.4-9.5, §11.3): the response lists the registered help topics and
        may name the nearest specialist — it never selects or executes a
        specialist and performs no retrieval or LLM call (§9.5). The turn is
        returned through the existing ``AgentOutput`` contract with
        ``WorkflowStatus.CLARIFYING``; the routing signal, conversation
        identity/context, memory history, and ``current_agent``/``handoff``
        are all preserved. Clarification behavior lives on the Coordinator
        (``CoordinatorAgent.clarify``), matching the §13.2 prompt-ownership
        boundary without inventing a dedicated prompt — the architecture
        defines no clarification prompt type, and the graph never hardcodes
        clarifying text.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ai.agents.base import SpecialistAgent
from ai.agents.coordinator import CoordinatorAgent, create_coordinator
from ai.core.state import (
    AgentKey,
    AgentOutput,
    ChatTurn,
    Handoff,
    MessageRole,
    WorkflowState,
    WorkflowStatus,
)
from ai.memory.manager import ConversationMemoryManager

NODE_DETECT_INTENT = "detect_intent"
NODE_ROUTE = "route"
NODE_CLARIFY = "clarify"
NODE_RETRIEVE = "retrieve"
NODE_BUILD_CONTEXT = "build_context"
NODE_GENERATE = "generate"
NODE_ASSEMBLE_CITATIONS = "assemble_citations"
NODE_AGGREGATE_RESPONSE = "aggregate_response"
NODE_PERSIST = "persist"


def _retrieve_with(
    specialists: Mapping[AgentKey, SpecialistAgent] | None,
    state: WorkflowState,
) -> dict[str, object]:
    """Retrieve node: delegate to the routed specialist (AI_ARCHITECTURE.md §11.2).

    The selected specialist encapsulates the entire specialist phase — retrieval
    (§16), context building (§17), generation (§18), citations (§19), response
    assembly, guardrails and fallbacks (§20, §25-26) — so the node invokes
    ``agent.run`` and records the resulting ``AgentOutput`` in
    ``state.agent_output`` (§11.2, §12.3). The agent is looked up by the
    router's ``selected_agent`` in the injected ``specialists`` map. A graph
    compiled without the injected specialist raises rather than silently
    skipping the phase (no false production behavior); a missing routing signal
    or the tentative Coordinator is a no-op (it never reaches this node via the
    router edge anyway, §11.3).
    """
    signal = state.routing_signal
    if signal is None or signal.selected_agent is AgentKey.COORDINATOR:
        return {}
    agent = specialists.get(signal.selected_agent) if specialists else None
    if agent is None:
        raise NotImplementedError(
            f"No specialist configured for '{signal.selected_agent}'; inject "
            "specialists via build_workflow(specialists=...)."
        )
    output = agent.run(
        query=state.user_query,
        message_history=state.message_history,
        user_context=state.user_context,
    )
    return {"agent_output": output}


def _build_context_with(state: WorkflowState) -> dict[str, object]:
    """Build-context node (AI_ARCHITECTURE.md §11.2) — pass-through.

    Context construction within budget is part of the specialist's ``run``
    pipeline (§13.5, §17); the workflow node is an honest no-op so the graph
    shape mirrors §11.1 without duplicating or re-framing the agent output.
    """
    return {}


def _generate_with(state: WorkflowState) -> dict[str, object]:
    """Generate node (AI_ARCHITECTURE.md §11.2) — pass-through.

    Structured, grounded generation runs inside the specialist agent (§18);
    the workflow node is an honest no-op.
    """
    return {}


def _assemble_citations_with(state: WorkflowState) -> dict[str, object]:
    """Assemble-citations node (AI_ARCHITECTURE.md §11.2) — pass-through.

    Citation assembly from cited chunk ids runs inside the specialist agent
    (§19); the workflow node is an honest no-op.
    """
    return {}


def _aggregate_response_with(state: WorkflowState) -> dict[str, object]:
    """Aggregate-response node (AI_ARCHITECTURE.md §11.2) — pass-through.

    The response envelope and handoff metadata are assembled inside the
    specialist agent (§20); the workflow node is an honest no-op.
    """
    return {}


def _noop_persist(history: Sequence[ChatTurn]) -> object:
    """Default memory writer: in-memory only (no backend DB in Phase 8)."""
    return None


def _persist_with(
    memory: ConversationMemoryManager,
    state: WorkflowState,
    *,
    writer: Callable[[Sequence[ChatTurn]], object] | None = None,
) -> dict[str, object]:
    """Persist node (AI_ARCHITECTURE.md §11.2, §21, §23.1).

    Appends the user query and the specialist's answer to the short-term memory
    window and best-effort persists the window through the injectable writer. A
    persistence failure never fails the run (§23.1) — the manager swallows
    writer errors — and the node still returns the updated window as the new
    ``message_history`` so the next turn carries this exchange in context.
    Without an ``agent_output`` the node is a no-op.
    """
    if state.agent_output is None:
        return {}
    history = state.message_history
    history, _ = memory.add_turn(history, role=MessageRole.USER, content=state.user_query)
    window, _ = memory.add_turn(
        history, role=MessageRole.ASSISTANT, content=state.agent_output.answer
    )
    memory.persist(window, writer or _noop_persist)
    return {"message_history": window}


def _detect_intent_with(
    coordinator: CoordinatorAgent,
    state: WorkflowState,
    *,
    memory: ConversationMemoryManager | None = None,
) -> dict[str, object]:
    """Detect-intent node backed by the Coordinator (§4.1, §11.2).

    The short-term memory window is enforced before classification so the
    Coordinator only ever sees the recent ``CHAT_HISTORY_LIMIT`` turns
    (AI_ARCHITECTURE.md §12.5, §21.2).
    """
    history = (
        memory.window(state.message_history) if memory is not None else state.message_history
    )
    signal = coordinator.detect_intent(
        state.user_query,
        message_history=history,
        user_context=state.user_context,
    )
    return {"routing_signal": signal}


def _route_with(coordinator: CoordinatorAgent, state: WorkflowState) -> dict[str, object]:
    """Route node backed by the Coordinator (§9.2, §11.2).

    Resolves the tentative Coordinator agent to a specialist when the signal is
    confident and mapped; unresolved signals keep the tentative Coordinator so
    the router edge returns a clarifying turn (§9.4-9.5). A resolved route
    records the active agent and the §24 handoff metadata: the routing signal
    is the new agent, ``current_agent`` tracks the last handoff (§24.3-24.4),
    and ``handoff`` carries ``(routed_to, previous_agent, reason)`` for the
    response envelope — recorded only on an actual agent change (§24.2).
    """
    signal = state.routing_signal
    if signal is None:
        return {}
    resolved = coordinator.route(signal)
    if resolved is None:
        return {}
    previous = state.current_agent or AgentKey.COORDINATOR
    updates: dict[str, object] = {
        "routing_signal": signal.model_copy(update={"selected_agent": resolved}),
        "current_agent": resolved,
    }
    if previous is not resolved:
        updates["handoff"] = Handoff(
            routed_to=resolved,
            previous_agent=previous,
            reason=signal.reason,
        )
    return updates


def _clarify_with(
    coordinator: CoordinatorAgent,
    state: WorkflowState,
) -> dict[str, object]:
    """Clarify node (AI_ARCHITECTURE.md §11.3, §11.5; §9.4-9.5).

    Produces the grounded clarifying turn for ambiguous, unknown, or
    out-of-scope signals and returns it through the ``AgentOutput`` contract
    with ``WorkflowStatus.CLARIFYING`` (§4.6, §11.6). The text is built by the
    Coordinator (``CoordinatorAgent.clarify``) from the registered help topics
    — deterministic and data-driven, never hardcoded in the graph (§13.2
    ownership: clarification behavior belongs to the Coordinator prompt, and
    the architecture defines no dedicated clarification prompt type).

    Safety/state semantics:
    - never selects or executes a specialist and performs no retrieval and no
      LLM call (§9.5 — the Coordinator never guesses),
    - the original ``routing_signal`` is preserved untouched,
    - ``conversation_id``, ``user_context``, ``message_history``, and
      ``current_agent``/``handoff`` are left unchanged (no handoff is recorded
      for a clarifying turn, §24),
    - the raw routing reason is never surfaced to the student (§26.3, §37).
    """
    answer = coordinator.clarify(state.routing_signal)
    return {
        "agent_output": AgentOutput(
            answer=answer,
            status=WorkflowStatus.CLARIFYING,
        )
    }


_default_coordinator: CoordinatorAgent | None = None
_default_memory: ConversationMemoryManager | None = None


def _get_default_coordinator() -> CoordinatorAgent:
    """Lazily built default Coordinator (rule-based; no API keys needed)."""
    global _default_coordinator
    if _default_coordinator is None:
        _default_coordinator = create_coordinator()
    return _default_coordinator


def _get_default_memory() -> ConversationMemoryManager:
    """Lazily built default memory manager (§21.2 window default 20 turns)."""
    global _default_memory
    if _default_memory is None:
        _default_memory = ConversationMemoryManager()
    return _default_memory


def detect_intent(state: WorkflowState) -> dict[str, object]:
    """Detect-intent node using the default Coordinator (§4.1, §11.2)."""
    return _detect_intent_with(
        _get_default_coordinator(),
        state,
        memory=_get_default_memory(),
    )


def route(state: WorkflowState) -> dict[str, object]:
    """Route node using the default Coordinator (§9.2, §11.2)."""
    return _route_with(_get_default_coordinator(), state)


def clarify(state: WorkflowState) -> dict[str, object]:
    """Clarify node using the default Coordinator (§11.3, §11.5; §9.4-9.5)."""
    return _clarify_with(_get_default_coordinator(), state)


def retrieve(state: WorkflowState) -> dict[str, object]:
    """Retrieve node without injected specialists.

    Raises ``NotImplementedError`` when a routed specialist has no configured
    agent; inject specialists via ``build_workflow(specialists=...)``.
    """
    return _retrieve_with(None, state)


def build_context(state: WorkflowState) -> dict[str, object]:
    """Build-context node (§11.2) — pass-through; see ``_build_context_with``."""
    return _build_context_with(state)


def generate(state: WorkflowState) -> dict[str, object]:
    """Generate node (§11.2) — pass-through; see ``_generate_with``."""
    return _generate_with(state)


def assemble_citations(state: WorkflowState) -> dict[str, object]:
    """Assemble-citations node (§11.2) — pass-through; see ``_assemble_citations_with``."""
    return _assemble_citations_with(state)


def aggregate_response(state: WorkflowState) -> dict[str, object]:
    """Aggregate-response node (§11.2) — pass-through; see ``_aggregate_response_with``."""
    return _aggregate_response_with(state)


def persist(state: WorkflowState) -> dict[str, object]:
    """Persist node using the default memory and an in-memory writer (§21, §23.1)."""
    return _persist_with(_get_default_memory(), state)


def route_after_detect(state: WorkflowState) -> str:
    """Router edge decision after intent detection (AI_ARCHITECTURE.md §11.3).

    A routing signal that resolved to a specialist enters the specialist phase
    (``retrieve``); a missing signal or one that kept the tentative Coordinator
    (ambiguous, unknown, or out-of-scope) returns a clarifying turn
    (``clarify``) per §9.4 and §28.
    """
    signal = state.routing_signal
    if signal is None or signal.selected_agent is AgentKey.COORDINATOR:
        return NODE_CLARIFY
    return NODE_RETRIEVE


def build_workflow(
    coordinator: CoordinatorAgent | None = None,
    memory: ConversationMemoryManager | None = None,
    specialists: Mapping[AgentKey, SpecialistAgent] | None = None,
    persist_writer: Callable[[Sequence[ChatTurn]], object] | None = None,
) -> CompiledStateGraph:
    """Construct and compile the LangGraph workflow (AI_ARCHITECTURE.md §11).

    The graph mirrors the §11.1-11.3 node/edge model using the typed
    ``WorkflowState`` (AI_ARCHITECTURE.md §10.2, §12). Compiling performs no
    node execution and requires no API keys or external services. Without a
    ``coordinator`` the deterministic rule-based Coordinator is used; pass the
    LLM-backed Coordinator (``create_llm_coordinator``) to route via the model
    gateway. The default ``memory`` enforces the §21.2 short-term window
    (``CHAT_HISTORY_LIMIT``); pass a custom ``ConversationMemoryManager`` (e.g.
    long-term opt-in) to change the window or summarization behavior.

    ``specialists`` maps ``AgentKey`` to the Phase 1 specialist agents; the
    retrieve node delegates to the agent selected by the router and records its
    ``AgentOutput`` in ``state.agent_output``. ``persist_writer`` is the memory
    persistence backend (backend DB writes arrive in Phase 10); without one the
    window is updated in-memory only. The clarify node is backed by the same
    injected ``coordinator`` (``CoordinatorAgent.clarify``) and returns a
    grounded clarifying ``AgentOutput`` without executing any specialist
    (Step 1L). The graph never constructs real LLM clients or retrievers —
    everything is injected.
    """
    resolved_coordinator = coordinator if coordinator is not None else _get_default_coordinator()
    resolved_memory = memory if memory is not None else _get_default_memory()
    builder = StateGraph(WorkflowState)

    builder.add_node(
        NODE_DETECT_INTENT,
        partial(_detect_intent_with, resolved_coordinator, memory=resolved_memory),
    )
    builder.add_node(NODE_ROUTE, partial(_route_with, resolved_coordinator))
    builder.add_node(
        NODE_RETRIEVE,
        partial(_retrieve_with, specialists),
    )
    builder.add_node(NODE_BUILD_CONTEXT, _build_context_with)
    builder.add_node(NODE_GENERATE, _generate_with)
    builder.add_node(NODE_ASSEMBLE_CITATIONS, _assemble_citations_with)
    builder.add_node(NODE_AGGREGATE_RESPONSE, _aggregate_response_with)
    builder.add_node(
        NODE_PERSIST,
        partial(_persist_with, resolved_memory, writer=persist_writer),
    )
    builder.add_node(NODE_CLARIFY, partial(_clarify_with, resolved_coordinator))

    builder.add_edge(START, NODE_DETECT_INTENT)
    builder.add_edge(NODE_DETECT_INTENT, NODE_ROUTE)
    builder.add_conditional_edges(
        NODE_ROUTE,
        route_after_detect,
        {
            NODE_RETRIEVE: NODE_RETRIEVE,
            NODE_CLARIFY: NODE_CLARIFY,
        },
    )
    builder.add_edge(NODE_RETRIEVE, NODE_BUILD_CONTEXT)
    builder.add_edge(NODE_BUILD_CONTEXT, NODE_GENERATE)
    builder.add_edge(NODE_GENERATE, NODE_ASSEMBLE_CITATIONS)
    builder.add_edge(NODE_ASSEMBLE_CITATIONS, NODE_AGGREGATE_RESPONSE)
    builder.add_edge(NODE_AGGREGATE_RESPONSE, NODE_PERSIST)
    builder.add_edge(NODE_PERSIST, END)
    builder.add_edge(NODE_CLARIFY, END)

    return builder.compile()

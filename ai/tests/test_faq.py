"""FAQ Agent, prompt, routing-integration, and error-safety tests.

Sources: AI_ARCHITECTURE.md §7 (FAQ Agent), §3.5/§12.3 (stateless
specialists), §9 (Coordinator routing), §13/§34 (prompts), §16 (retrieval),
§17 (context building), §18 (generation), §19 (citations), §20.4/§28.3
(no-answer policy), §23 (error recovery). All behavior is deterministic — a
fake retriever and a fake gateway are injected, and the Coordinator uses the
deterministic rule-based classifier, so the suite runs fully offline (mocked
LLM, TESTING_STRATEGY.md §23.2). No Gemini/OpenAI/Groq key, network, database,
or backend service is required.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Any

import pytest

from ai.agents.coordinator import CoordinatorAgent
from ai.agents.faq import FAQAgent, create_faq_agent
from ai.core.config import Settings
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
from ai.gateway.base import LLMGateway, LLMProviderError, LLMResponse, LLMTimeoutError
from ai.graphs.workflow import NODE_CLARIFY, NODE_RETRIEVE, route_after_detect
from ai.prompts.repository import PromptRepository, default_repository
from ai.prompts.versions.faq_v1 import PROMPT_KEY, PROMPT_VERSION
from ai.rag.retriever import Retriever


def _chunk(
    chunk_id: str,
    *,
    score: float = 0.8,
    title: str = "Campus Guide",
    snippet: str = "The library is open from 9:00 am to 5:00 pm on weekdays.",
    category: str = "faq",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        title=title,
        category=category,
        snippet=snippet,
        score=score,
    )


def _llm_json(
    *,
    answer: str = "The library is open from 9:00 am to 5:00 pm on weekdays.",
    cited_chunk_ids: list[str] | None = None,
    unanswerable: bool = False,
) -> str:
    return json.dumps(
        {
            "answer": answer,
            "cited_chunk_ids": cited_chunk_ids or [],
            "unanswerable": unanswerable,
            "reason": "grounded in campus guide",
        }
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


class FakeGateway(LLMGateway):
    """Scripted fake gateway for offline specialist tests."""

    def __init__(self, *, content: str = "", error: Exception | None = None) -> None:
        super().__init__(model="fake-model", max_retries=0)
        self.content = content
        self.error = error
        self.calls: list[dict[str, object]] = []

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
        self.calls.append(
            {
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "json_schema": json_schema,
            }
        )
        if self.error is not None:
            raise self.error
        return LLMResponse(content=self.content, model=model)


def _make_agent(
    *,
    chunks: list[RetrievedChunk] | None = None,
    gateway: FakeGateway | None = None,
    **kwargs: Any,
) -> tuple[FAQAgent, FakeRetriever, FakeGateway]:
    retriever = FakeRetriever(chunks)
    fake_gateway = gateway or FakeGateway(content=_llm_json())
    agent = FAQAgent(
        retriever=retriever,
        gateway=fake_gateway,
        **kwargs,
    )
    return agent, retriever, fake_gateway


# --- Prompt ownership (AI_ARCHITECTURE.md §13.1, §34) ------------------------


def test_default_repository_registers_faq_prompt() -> None:
    prompt = default_repository().get(PROMPT_KEY)
    assert prompt is not None
    assert prompt.version == PROMPT_VERSION
    assert prompt.agent_key is AgentKey.FAQ


def test_faq_agent_owns_its_versioned_prompt() -> None:
    agent, _, _ = _make_agent()
    assert agent.prompt.key == PROMPT_KEY
    assert agent.prompt.version == PROMPT_VERSION


def test_faq_prompt_composes_shared_components() -> None:
    agent, _, _ = _make_agent()
    text = agent.prompt.text.lower()
    assert "answer only from the retrieved evidence" in text
    assert "no-answer policy" in text
    assert "registrar's office" in text


def test_faq_prompt_reflects_architecture_scope() -> None:
    # §7.1-7.3 scope: FAQs, departments/services, office timings, campus, contacts.
    agent, _, _ = _make_agent()
    text = agent.prompt.text.lower()
    assert "general university faqs" in text
    assert "departments and services" in text
    assert "office timings" in text
    assert "campus information" in text
    assert "contact information" in text
    # §7.4 limitations: general-answer only, no fabricated institutional facts,
    # contact details restated only from the source so staleness is visible.
    assert "general-answer only" in text
    assert "never invent policies" in text
    assert "contact details change" in text


def test_missing_prompt_fails_fast() -> None:
    with pytest.raises(ValueError):
        _make_agent(prompt_repository=PromptRepository())


# --- Retrieval (AI_ARCHITECTURE.md §16.4) ------------------------------------


def test_retrieve_scopes_to_faq_category_and_top_k() -> None:
    agent, retriever, _ = _make_agent(top_k=3)
    agent.retrieve(query="What are the university office hours?")
    assert retriever.calls[-1]["query"] == "What are the university office hours?"
    assert retriever.calls[-1]["categories"] == ("faq",)
    assert retriever.calls[-1]["top_k"] == 3


def test_create_faq_agent_configures_from_settings() -> None:
    settings = Settings(rag_top_k=2, context_budget_tokens=512, llm_temperature=0.0)
    agent = create_faq_agent(
        settings=settings,
        retriever=FakeRetriever(),
        gateway=FakeGateway(content=_llm_json()),
    )
    assert agent.AGENT_KEY is AgentKey.FAQ
    assert agent.categories == ("faq",)
    assert agent.top_k == 2
    assert agent.prompt.version == PROMPT_VERSION


# --- No-answer policy (AI_ARCHITECTURE.md §20.4, §28.3) ----------------------


def test_no_evidence_short_circuits_to_no_answer_without_llm_call() -> None:
    gateway = FakeGateway(content=_llm_json())
    agent, _, gateway = _make_agent(chunks=[], gateway=gateway)
    output = agent.run(query="How do I contact the registrar?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer
    assert "Registrar's Office" in output.answer
    assert output.citations == []
    assert gateway.calls == []


def test_empty_query_without_evidence_returns_safe_no_answer() -> None:
    gateway = FakeGateway(content=_llm_json())
    agent, _, gateway = _make_agent(chunks=[], gateway=gateway)
    output = agent.run(query="")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer
    assert gateway.calls == []


def test_llm_unanswerable_triggers_no_answer() -> None:
    gateway = FakeGateway(content=_llm_json(unanswerable=True))
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="When does the registrar's office open?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer
    assert "Registrar's Office" in output.answer


def test_empty_llm_answer_treated_as_unanswerable() -> None:
    gateway = FakeGateway(content=_llm_json(answer="  "))
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="Where is the library?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer


# --- Grounded generation + citations (AI_ARCHITECTURE.md §18-19) -------------


def test_run_returns_grounded_answer_with_citations() -> None:
    chunks = [
        _chunk("c1", score=0.9, title="Office Timings", snippet="9:00 am to 5:00 pm."),
        _chunk("c2", score=0.7, title="Contacts", snippet="021-99333771."),
    ]
    gateway = FakeGateway(
        content=_llm_json(
            cited_chunk_ids=["c2", "c1"],
            answer="Office hours are 9:00 am to 5:00 pm.",
        )
    )
    agent, _, gateway = _make_agent(chunks=chunks, gateway=gateway)
    output = agent.run(query="What are the university office hours?")
    assert output.status is WorkflowStatus.COMPLETED
    assert output.answer == "Office hours are 9:00 am to 5:00 pm."
    titles = [c.title for c in output.citations]
    assert titles == ["Office Timings", "Contacts"]  # score order (§19.3)
    assert output.citations[0].chunk_id == "c1"
    assert output.citations[0].relevance_score == pytest.approx(0.9)


def test_citations_deduplicated_and_unknown_ids_ignored() -> None:
    chunks = [_chunk("c1", score=0.8)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1", "c1", "ghost"]))
    agent, _, _ = _make_agent(chunks=chunks, gateway=gateway)
    output = agent.run(query="campus info?")
    assert len(output.citations) == 1
    assert output.citations[0].chunk_id == "c1"


def test_citation_relevance_score_clamped_to_unit_range() -> None:
    chunks = [_chunk("hi", score=1.4), _chunk("lo", score=-0.2)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["hi", "lo"]))
    agent, _, _ = _make_agent(chunks=chunks, gateway=gateway)
    output = agent.run(query="scores?")
    assert output.citations[0].relevance_score == pytest.approx(1.0)
    assert output.citations[1].relevance_score == pytest.approx(0.0)


def test_generation_is_schema_constrained_structured_output() -> None:
    gateway = FakeGateway(content=_llm_json())
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    agent.run(query="What departments does the university have?")
    schema = gateway.calls[0]["json_schema"]
    assert isinstance(schema, dict)
    assert schema["type"] == "object"
    assert "answer" in schema["properties"]
    assert "cited_chunk_ids" in schema["properties"]
    assert "unanswerable" in schema["properties"]


def test_generation_passes_prompt_evidence_history_and_user_context() -> None:
    gateway = FakeGateway(content=_llm_json())
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    agent.run(
        query="Where is it?",
        message_history=[
            ChatTurn(role=MessageRole.USER, content="What is the library address?")
        ],
        user_context=UserContext(
            user_id=uuid.uuid4(), user_role=UserRole.STUDENT, department="CS"
        ),
    )
    call = gateway.calls[0]
    assert call["system_prompt"] == agent.prompt.text
    assert "[Retrieved evidence" in str(call["user_prompt"])
    assert "[Conversation history]" in str(call["user_prompt"])
    assert "[User context]" in str(call["user_prompt"])
    assert "Where is it?" in str(call["user_prompt"])


def test_retrieved_context_content_reaches_the_pipeline() -> None:
    gateway = FakeGateway(content=_llm_json())
    agent, _, gateway = _make_agent(chunks=[_chunk("c1", snippet="Library: Main Block.")])
    agent.run(query="Where is the library?")
    call = gateway.calls[0]
    assert "Library: Main Block." in str(call["user_prompt"])


# --- WorkflowState + AgentOutput (AI_ARCHITECTURE.md §10.2, §3.3) -----------


def test_faq_run_accepts_workflow_state_fields_and_returns_agent_output() -> None:
    state = WorkflowState(
        user_query="Where is the library?",
        message_history=[
            ChatTurn(role=MessageRole.USER, content="I need campus information.")
        ],
        user_context=UserContext(
            user_id=uuid.uuid4(), user_role=UserRole.STUDENT, department="CS"
        ),
    )
    agent, _, _ = _make_agent(chunks=[_chunk("c1")])
    output = agent.run(
        query=state.user_query,
        message_history=state.message_history,
        user_context=state.user_context,
    )
    assert isinstance(output, AgentOutput)
    assert output.status is WorkflowStatus.COMPLETED
    assert output.answer
    assert isinstance(output.citations, list)
    assert all(isinstance(citation, Citation) for citation in output.citations)
    completed = state.model_copy(update={"agent_output": output})
    assert completed.agent_output is output


# --- Error safety (AI_ARCHITECTURE.md §23.2) ---------------------------------


def test_provider_failure_degrades_to_friendly_fallback() -> None:
    gateway = FakeGateway(error=LLMProviderError("upstream failed"))
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="office timings?")
    assert output.status is WorkflowStatus.FALLBACK
    assert "trouble generating" in output.answer
    assert "upstream failed" not in output.answer


def test_timeout_failure_degrades_to_friendly_fallback() -> None:
    gateway = FakeGateway(error=LLMTimeoutError("request timed out"))
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="office timings?")
    assert output.status is WorkflowStatus.FALLBACK
    assert "trouble generating" in output.answer
    assert "timed out" not in output.answer


def test_provider_error_secrets_never_surface_in_answer() -> None:
    gateway = FakeGateway(error=LLMProviderError("boom sk-abcdefghijklmnop123456"))
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="office timings?")
    assert "sk-abcdefghijklmnop123456" not in output.answer


def test_malformed_provider_output_degrades_to_no_answer() -> None:
    gateway = FakeGateway(content="not json at all")
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="office timings?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer


# --- Coordinator / routing integration (AI_ARCHITECTURE.md §9) ---------------


def test_rule_based_classifier_recognizes_clear_faq_request() -> None:
    coordinator = CoordinatorAgent()
    signal = coordinator.detect_intent("What are the university office hours?")
    assert signal.intent is IntentCategory.FAQ
    assert coordinator.route(signal) is AgentKey.FAQ


def test_registry_resolves_faq_intent() -> None:
    coordinator = CoordinatorAgent()
    assert coordinator.registry.resolve(IntentCategory.FAQ) is AgentKey.FAQ


def test_registry_resolves_general_intent_to_faq() -> None:
    # Unspecific/general messages route to the FAQ specialist (§4.2, §9.2).
    coordinator = CoordinatorAgent()
    assert coordinator.registry.resolve(IntentCategory.GENERAL) is AgentKey.FAQ


def test_coordinator_routes_faq_query_to_faq_agent() -> None:
    coordinator = CoordinatorAgent()
    signal = coordinator.detect_intent("How do I contact the registrar?")
    assert signal.intent is IntentCategory.FAQ
    assert coordinator.route(signal) is AgentKey.FAQ


def test_coordinator_route_uses_faq_intent_without_classifier() -> None:
    coordinator = CoordinatorAgent()
    signal = RoutingSignal(
        intent=IntentCategory.FAQ,
        selected_agent=AgentKey.COORDINATOR,
        confidence=0.9,
    )
    assert coordinator.route(signal) is AgentKey.FAQ


def test_router_edge_sends_resolved_faq_signal_to_retrieve() -> None:
    # A routing signal resolved to the FAQ specialist enters the specialist
    # phase (retrieve), preserving the §11.3 edge semantics.
    state = WorkflowState(
        user_query="What are the university office hours?",
        routing_signal=RoutingSignal(
            intent=IntentCategory.FAQ,
            selected_agent=AgentKey.FAQ,
            confidence=0.9,
        ),
    )
    assert route_after_detect(state) == NODE_RETRIEVE


def test_router_edge_keeps_unresolved_faq_signal_in_clarify() -> None:
    # A low-confidence signal keeps the tentative Coordinator -> clarify (§9.4).
    state = WorkflowState(
        user_query="What are the university office hours?",
        routing_signal=RoutingSignal(
            intent=IntentCategory.FAQ,
            selected_agent=AgentKey.COORDINATOR,
            confidence=0.2,
        ),
    )
    assert route_after_detect(state) == NODE_CLARIFY


# --- Retriever contract (AI_ARCHITECTURE.md §16) -----------------------------


def test_retriever_protocol_is_importable_and_typed() -> None:
    # The protocol exists so Phase 9 can implement it behind the same contract.
    assert Retriever is not None
    retriever = FakeRetriever(chunks=[_chunk("c1")])
    assert isinstance(retriever, Retriever)

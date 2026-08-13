"""Admission Agent, specialist machinery, prompts, and context-builder tests.

Sources: AI_ARCHITECTURE.md §5 (Admission Agent), §3.5/§12.3 (stateless
specialists), §13/§34 (prompts), §16 (retrieval), §17 (context building),
§18 (generation), §19 (citations), §20.4/§28.3 (no-answer policy), §23
(error recovery). All behavior is deterministic — a fake retriever and a fake
gateway are injected, so the suite runs fully offline (mocked LLM,
TESTING_STRATEGY.md §23.2).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Any

import pytest

from ai.agents.admission import AdmissionAgent, create_admission_agent
from ai.core.config import Settings
from ai.core.state import (
    AgentKey,
    ChatTurn,
    MessageRole,
    RetrievedChunk,
    UserContext,
    UserRole,
    WorkflowStatus,
)
from ai.gateway.base import LLMGateway, LLMProviderError, LLMResponse
from ai.prompts.repository import PromptRepository, default_repository
from ai.prompts.versions.admission_v1 import PROMPT_KEY, PROMPT_VERSION
from ai.rag.context_builder import ContextBuilder, ContextOverflowError
from ai.rag.retriever import Retriever


def _chunk(
    chunk_id: str,
    *,
    score: float = 0.8,
    title: str = "Admission Policy",
    snippet: str = "Applicants need 60% in intermediate to be eligible.",
    category: str = "admission",
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
    answer: str = "You are eligible with 60% in intermediate.",
    cited_chunk_ids: list[str] | None = None,
    unanswerable: bool = False,
) -> str:
    return json.dumps(
        {
            "answer": answer,
            "cited_chunk_ids": cited_chunk_ids or [],
            "unanswerable": unanswerable,
            "reason": "grounded in merit policy",
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
) -> tuple[AdmissionAgent, FakeRetriever, FakeGateway]:
    retriever = FakeRetriever(chunks)
    fake_gateway = gateway or FakeGateway(content=_llm_json())
    agent = AdmissionAgent(
        retriever=retriever,
        gateway=fake_gateway,
        **kwargs,
    )
    return agent, retriever, fake_gateway


# --- Prompt ownership (AI_ARCHITECTURE.md §13.1, §34) ------------------------


def test_default_repository_registers_admission_prompt() -> None:
    prompt = default_repository().get(PROMPT_KEY)
    assert prompt is not None
    assert prompt.version == PROMPT_VERSION
    assert prompt.agent_key is AgentKey.ADMISSION


def test_admission_agent_owns_its_versioned_prompt() -> None:
    agent, _, _ = _make_agent()
    assert agent.prompt.key == PROMPT_KEY
    assert agent.prompt.version == PROMPT_VERSION


def test_admission_prompt_composes_shared_components() -> None:
    agent, _, _ = _make_agent()
    text = agent.prompt.text.lower()
    assert "admission" in text
    assert "answer only from the retrieved evidence" in text
    assert "no-answer policy" in text
    assert "smiu admission office" in text


def test_missing_prompt_fails_fast() -> None:
    with pytest.raises(ValueError):
        _make_agent(prompt_repository=PromptRepository())


# --- Retrieval (AI_ARCHITECTURE.md §16.4) ------------------------------------


def test_retrieve_scopes_to_admission_category_and_top_k() -> None:
    agent, retriever, _ = _make_agent(top_k=3)
    agent.retrieve(query="What are the requirements?")
    assert retriever.calls[-1]["query"] == "What are the requirements?"
    assert retriever.calls[-1]["categories"] == ("admission",)
    assert retriever.calls[-1]["top_k"] == 3


def test_create_admission_agent_configures_from_settings() -> None:
    settings = Settings(rag_top_k=2, context_budget_tokens=512, llm_temperature=0.0)
    agent = create_admission_agent(
        settings=settings,
        retriever=FakeRetriever(),
        gateway=FakeGateway(content=_llm_json()),
    )
    assert agent.AGENT_KEY is AgentKey.ADMISSION
    assert agent.categories == ("admission",)
    assert agent.top_k == 2
    assert agent.prompt.version == PROMPT_VERSION


# --- No-answer policy (AI_ARCHITECTURE.md §20.4, §28.3) ----------------------


def test_no_evidence_short_circuits_to_no_answer_without_llm_call() -> None:
    gateway = FakeGateway(content=_llm_json())
    agent, _, gateway = _make_agent(chunks=[], gateway=gateway)
    output = agent.run(query="What documents do I need?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer
    assert "Admission Office" in output.answer
    assert output.citations == []
    assert gateway.calls == []


def test_llm_unanswerable_triggers_no_answer() -> None:
    gateway = FakeGateway(content=_llm_json(unanswerable=True))
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="Am I eligible?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer
    assert "Admission Office" in output.answer


def test_empty_llm_answer_treated_as_unanswerable() -> None:
    gateway = FakeGateway(content=_llm_json(answer="  "))
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="Am I eligible?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer


# --- Grounded generation + citations (AI_ARCHITECTURE.md §18-19) -------------


def test_run_returns_grounded_answer_with_citations() -> None:
    chunks = [
        _chunk("c1", score=0.9, title="Merit Policy", snippet="60% required."),
        _chunk("c2", score=0.7, title="Documents", snippet="Two photocopies."),
    ]
    gateway = FakeGateway(
        content=_llm_json(cited_chunk_ids=["c2", "c1"], answer="Here is the policy.")
    )
    agent, _, gateway = _make_agent(chunks=chunks, gateway=gateway)
    output = agent.run(query="What is the merit policy?")
    assert output.status is WorkflowStatus.COMPLETED
    assert output.answer == "Here is the policy."
    titles = [c.title for c in output.citations]
    assert titles == ["Merit Policy", "Documents"]  # score order (§19.3)
    assert output.citations[0].chunk_id == "c1"
    assert output.citations[0].relevance_score == pytest.approx(0.9)


def test_citations_deduplicated_and_unknown_ids_ignored() -> None:
    chunks = [_chunk("c1", score=0.8)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1", "c1", "ghost"]))
    agent, _, _ = _make_agent(chunks=chunks, gateway=gateway)
    output = agent.run(query="documents?")
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
    agent.run(query="eligibility?")
    schema = gateway.calls[0]["json_schema"]
    assert isinstance(schema, dict)
    assert schema["type"] == "object"
    assert "answer" in schema["properties"]
    assert "cited_chunk_ids" in schema["properties"]
    assert "unanswerable" in schema["properties"]


def test_generation_passes_prompt_and_built_context() -> None:
    gateway = FakeGateway(content=_llm_json())
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    agent.run(
        query="What is the deadline?",
        message_history=[ChatTurn(role=MessageRole.USER, content="About admission")],
        user_context=UserContext(
            user_id=uuid.uuid4(), user_role=UserRole.STUDENT, department="CS"
        ),
    )
    call = gateway.calls[0]
    assert call["system_prompt"] == agent.prompt.text
    assert "[Retrieved evidence" in str(call["user_prompt"])
    assert "What is the deadline?" in str(call["user_prompt"])


# --- Error safety (AI_ARCHITECTURE.md §23.2) ---------------------------------


def test_provider_failure_degrades_to_friendly_fallback() -> None:
    gateway = FakeGateway(error=LLMProviderError("upstream failed"))
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="eligibility?")
    assert output.status is WorkflowStatus.FALLBACK
    assert "trouble generating" in output.answer
    assert "upstream failed" not in output.answer


def test_provider_error_secrets_never_surface_in_answer() -> None:
    gateway = FakeGateway(error=LLMProviderError("boom sk-abcdefghijklmnop123456"))
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="eligibility?")
    assert "sk-abcdefghijklmnop123456" not in output.answer


def test_malformed_provider_output_degrades_to_no_answer() -> None:
    gateway = FakeGateway(content="not json at all")
    agent, _, gateway = _make_agent(chunks=[_chunk("c1")], gateway=gateway)
    output = agent.run(query="eligibility?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer


# --- Context builder (AI_ARCHITECTURE.md §17.2-17.4) -------------------------


def _char_estimator(text: str) -> int:
    return len(text)


def test_context_builder_orders_sections_and_labels() -> None:
    builder = ContextBuilder(max_tokens=10_000, estimate_tokens=_char_estimator)
    context = builder.build(
        query="What is the deadline?",
        evidence=[_chunk("c1", score=0.9)],
        message_history=[ChatTurn(role=MessageRole.USER, content="About admission")],
        user_context=UserContext(user_id=uuid.uuid4(), user_role=UserRole.STUDENT),
        system_rules="SYSTEM RULES",
    )
    assert context.index("SYSTEM RULES") < context.index("[User context]")
    assert context.index("[User context]") < context.index("[Conversation history]")
    assert context.index("[Conversation history]") < context.index("[Retrieved evidence")
    assert context.index("[Retrieved evidence") < context.index("[Current question]")


def test_context_builder_trims_lowest_score_evidence_first() -> None:
    builder = ContextBuilder(max_tokens=150, estimate_tokens=_char_estimator)
    context = builder.build(
        query="deadline?",
        evidence=[
            _chunk("high", score=0.9, snippet="high-scoring merit policy content"),
            _chunk("low", score=0.1, snippet="low-scoring stale content"),
        ],
    )
    assert "high-scoring merit policy content" in context
    assert "low-scoring stale content" not in context
    assert "deadline?" in context


def test_context_builder_drops_user_context_before_evidence() -> None:
    builder = ContextBuilder(max_tokens=150, estimate_tokens=_char_estimator)
    context = builder.build(
        query="deadline?",
        evidence=[_chunk("keep", score=0.9, snippet="keep this evidence block")],
        user_context=UserContext(user_id=uuid.uuid4(), user_role=UserRole.STUDENT),
    )
    assert "keep this evidence block" in context
    assert "[User context]" not in context


def test_context_builder_trims_oldest_history_first() -> None:
    builder = ContextBuilder(max_tokens=60, estimate_tokens=_char_estimator)
    history = [
        ChatTurn(role=MessageRole.USER, content="oldest turn that is long enough"),
        ChatTurn(role=MessageRole.USER, content="recent turn"),
    ]
    context = builder.build(query="next?", message_history=history)
    assert "recent turn" in context
    assert "oldest turn" not in context


def test_context_builder_raises_when_essential_content_exceeds_budget() -> None:
    builder = ContextBuilder(max_tokens=10, estimate_tokens=_char_estimator)
    with pytest.raises(ContextOverflowError):
        builder.build(
            query="a question that is much longer than ten characters",
            system_rules="system rules that also exceed the budget",
        )


# --- Retriever contract (AI_ARCHITECTURE.md §16) -----------------------------


def test_retriever_protocol_is_importable_and_typed() -> None:
    # The protocol exists so Phase 9 can implement it behind the same contract.
    assert Retriever is not None
    retriever = FakeRetriever(chunks=[_chunk("c1")])
    assert isinstance(retriever, Retriever)

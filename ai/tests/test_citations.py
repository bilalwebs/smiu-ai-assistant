"""Citation generation + dedup tests (Phase 9 RAG task 6).

Sources: AI_ARCHITECTURE.md §19 (citation generation: §19.1 source
attribution, §19.3 multiple-source score ordering + per-chunk dedup, §19.4
confidence/score association), §16.3/§16.5 (ranking order + deterministic
position tie-break), §20.3-20.4 (source validation + no-answer policy),
DATABASE_DESIGN.md §32.6 (``ai_sources_score_check`` 0..1 constraint), §34.6
(versioned prompt traceability). All behavior is deterministic and fully
offline — a fake retriever and a fake gateway are injected, so the suite
runs with no API keys, no network, and no database (TESTING_STRATEGY.md §23.2).

The citation assembler in ``ai/agents/base.py`` is the single shared
implementation used by every specialist (Admission, Examination, FAQ) and
by GENERAL → FAQ routing through the LangGraph workflow.
"""

from __future__ import annotations

import json
import uuid

import pytest

from ai.agents.admission import AdmissionAgent
from ai.agents.coordinator import create_llm_coordinator
from ai.agents.examination import ExaminationAgent
from ai.agents.faq import FAQAgent, create_faq_agent
from ai.core.config import Settings
from ai.core.state import (
    AgentKey,
    AgentOutput,
    RetrievedChunk,
    WorkflowStatus,
)
from ai.graphs.workflow import build_workflow
from ai.tests.test_admission import FakeGateway, FakeRetriever
from ai.tests.test_admission import _chunk as _admission_chunk
from ai.tests.test_workflow_specialists import GeneralIntentGateway

_SETTINGS = Settings(
    rag_top_k=4,
    context_budget_tokens=4096,
    llm_provider="gemini",
    gemini_api_key="",
)


def _chunk(
    chunk_id: str,
    *,
    score: float = 0.8,
    title: str = "Admission Policy",
    snippet: str = "Applicants need 60% in intermediate to be eligible.",
    category: str = "admission",
    document_id: uuid.UUID | None = None,
) -> RetrievedChunk:
    return _admission_chunk(
        chunk_id,
        score=score,
        title=title,
        snippet=snippet,
        category=category,
    ).model_copy(update={"document_id": document_id})


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


def _invoke(graph: object, *, user_query: str, **state: object) -> object:
    """Run the compiled graph and return the coerced workflow state."""
    from ai.core.state import WorkflowState

    result = graph.invoke({"user_query": user_query, **state})  # type: ignore[attr-defined]
    return WorkflowState.model_validate(result)


# --- Source attribution (§19.1, §20.3) ---------------------------------------


def test_citations_derived_only_from_retrieved_chunk_metadata() -> None:
    doc_id = uuid.uuid4()
    chunks = [
        _chunk(
            "c1",
            score=0.9,
            title="Merit Policy",
            snippet="60% required.",
            category="admission",
            document_id=doc_id,
        )
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="What is the merit policy?")
    citation = output.citations[0]
    assert citation.chunk_id == "c1"
    assert citation.document_id == doc_id
    assert citation.title == "Merit Policy"
    assert citation.category == "admission"
    assert citation.snippet == "60% required."


def test_unknown_cited_ids_ignored_never_fabricated() -> None:
    chunks = [_chunk("c1")]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["ghost", "c1", "also-ghost"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert [cit.chunk_id for cit in output.citations] == ["c1"]


def test_llm_cannot_inject_source_metadata() -> None:
    chunks = [_chunk("c1", title="Merit Policy", snippet="60% required.")]
    gateway = FakeGateway(
        content=_llm_json(
            answer="Per the Official Prospectus 2026, the requirement is 60%.",
            cited_chunk_ids=["c1"],
        )
    )
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    citation = output.citations[0]
    assert citation.title == "Merit Policy"
    assert "Prospectus" not in citation.title
    assert citation.chunk_id == "c1"


def test_empty_retrieval_no_citations_and_no_llm_call() -> None:
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["ghost"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=[]), gateway=gateway)
    output = agent.run(query="documents?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer
    assert output.citations == []
    assert gateway.calls == []


def test_no_cited_ids_produces_no_citations() -> None:
    chunks = [_chunk("c1", score=0.9), _chunk("c2", score=0.7)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=[]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert output.answer
    assert output.citations == []


# --- Deduplication (§19.3) ---------------------------------------------------


def test_duplicate_chunk_id_cited_repeatedly_deduplicated() -> None:
    chunks = [_chunk("c1")]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1", "c1", "c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert len(output.citations) == 1
    assert output.citations[0].chunk_id == "c1"


def test_duplicate_chunk_in_retrieved_set_strongest_kept() -> None:
    chunks = [_chunk("c1", score=0.6), _chunk("c1", score=0.95)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert len(output.citations) == 1
    assert output.citations[0].chunk_id == "c1"
    assert output.citations[0].relevance_score == pytest.approx(0.95)


def test_distinct_chunks_from_same_document_not_merged() -> None:
    doc_id = uuid.uuid4()
    chunks = [
        _chunk("c1", score=0.9, title="Merit Policy", document_id=doc_id),
        _chunk("c2", score=0.8, title="Documents", document_id=doc_id),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1", "c2"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert [cit.chunk_id for cit in output.citations] == ["c1", "c2"]
    assert {cit.document_id for cit in output.citations} == {doc_id}


# --- Ordering (§19.3, §16.3/§16.5) -------------------------------------------


def test_citations_ordered_by_retrieval_score_descending() -> None:
    chunks = [
        _chunk("c1", score=0.9, title="Merit Policy"),
        _chunk("c2", score=0.7, title="Documents"),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c2", "c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert [cit.chunk_id for cit in output.citations] == ["c1", "c2"]


def test_equal_scores_tie_broken_by_retrieval_position_not_llm_order() -> None:
    chunks = [
        _chunk("c1", score=0.7, title="Merit Policy"),
        _chunk("c2", score=0.7, title="Documents"),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c2", "c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert [cit.chunk_id for cit in output.citations] == ["c1", "c2"]


def test_citation_ordering_identical_across_repeated_runs() -> None:
    chunks = [
        _chunk("c1", score=0.7),
        _chunk("c2", score=0.9),
        _chunk("c3", score=0.7),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c3", "c1", "c2"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    first = [cit.chunk_id for cit in agent.run(query="requirements?").citations]
    second = [cit.chunk_id for cit in agent.run(query="requirements?").citations]
    assert first == second == ["c2", "c1", "c3"]


def test_citation_order_never_follows_llm_order() -> None:
    chunks = [
        _chunk("c1", score=0.8, title="Merit Policy"),
        _chunk("c2", score=0.8, title="Documents"),
        _chunk("c3", score=0.8, title="Fees"),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c3", "c1", "c2"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert [cit.chunk_id for cit in output.citations] == ["c1", "c2", "c3"]


# --- Score handling (§19.4, DATABASE_DESIGN.md §32.6) ------------------------


def test_score_clamped_to_unit_range() -> None:
    chunks = [_chunk("hi", score=1.4), _chunk("lo", score=-0.2)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["hi", "lo"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="scores?")
    assert output.citations[0].relevance_score == pytest.approx(1.0)
    assert output.citations[1].relevance_score == pytest.approx(0.0)


def test_non_finite_scores_degrade_to_zero_without_crash() -> None:
    chunks = [_chunk("nan", score=float("nan")), _chunk("inf", score=float("inf"))]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["nan", "inf"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="scores?")
    assert output.status is WorkflowStatus.COMPLETED
    assert [cit.relevance_score for cit in output.citations] == [0.0, 0.0]
    assert [cit.chunk_id for cit in output.citations] == ["nan", "inf"]


def test_score_never_invented_for_uncited_chunks() -> None:
    chunks = [_chunk("c1", score=0.9), _chunk("c2", score=0.7)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert [cit.chunk_id for cit in output.citations] == ["c1"]


# --- Specialist pipeline integration (§12.3) ---------------------------------


def test_admission_agent_returns_grounded_citations() -> None:
    chunks = [
        _chunk("c1", score=0.9, category="admission"),
        _chunk("c2", score=0.7, category="admission"),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c2", "c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert output.status is WorkflowStatus.COMPLETED
    assert [cit.chunk_id for cit in output.citations] == ["c1", "c2"]


def test_examination_agent_returns_grounded_citations() -> None:
    chunks = [
        _chunk("x1", score=0.9, category="examination"),
        _chunk("x2", score=0.7, category="examination"),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["x2", "x1"]))
    agent = ExaminationAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="When are the results?")
    assert output.status is WorkflowStatus.COMPLETED
    assert [cit.chunk_id for cit in output.citations] == ["x1", "x2"]


def test_faq_agent_returns_grounded_citations() -> None:
    chunks = [
        _chunk("f1", score=0.9, category="faq"),
        _chunk("f2", score=0.7, category="faq"),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["f2", "f1"]))
    agent = FAQAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="What are the library hours?")
    assert output.status is WorkflowStatus.COMPLETED
    assert [cit.chunk_id for cit in output.citations] == ["f1", "f2"]


def test_general_routes_to_faq_with_citations() -> None:
    coordinator = create_llm_coordinator(settings=_SETTINGS, gateway=GeneralIntentGateway())
    answer_gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["f1"], answer="FAQ answer"))
    faq = create_faq_agent(
        settings=_SETTINGS,
        retriever=FakeRetriever(chunks=[_chunk("f1", category="faq")]),
        gateway=answer_gateway,
    )
    graph = build_workflow(coordinator=coordinator, specialists={AgentKey.FAQ: faq})
    result = _invoke(graph, user_query="Tell me something about the university")
    assert result.current_agent is AgentKey.FAQ  # type: ignore[attr-defined]
    assert result.agent_output.answer == "FAQ answer"  # type: ignore[attr-defined]
    assert [cit.chunk_id for cit in result.agent_output.citations] == ["f1"]  # type: ignore[attr-defined]


def test_agent_output_contract_preserved() -> None:
    chunks = [_chunk("c1", score=0.9)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1"], answer="Answer."))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert isinstance(output, AgentOutput)
    assert output.answer == "Answer."
    assert output.status is WorkflowStatus.COMPLETED
    assert isinstance(output.citations, list)
    assert output.citations[0].chunk_id == "c1"


def test_unanswerable_preserves_no_answer_and_only_evidence_citations() -> None:
    chunks = [_chunk("c1", score=0.9)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1"], unanswerable=True))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="Am I eligible?")
    assert output.status is WorkflowStatus.COMPLETED
    assert "not available" in output.answer
    for citation in output.citations:
        assert citation.chunk_id in {"c1"}


# --- Single-call guarantees (§16.5) ------------------------------------------


def test_retriever_called_exactly_once_per_run() -> None:
    retriever = FakeRetriever(chunks=[_chunk("c1")])
    agent = AdmissionAgent(retriever=retriever, gateway=FakeGateway(content=_llm_json()))
    agent.run(query="requirements?")
    assert len(retriever.calls) == 1


def test_llm_called_exactly_once_per_run() -> None:
    gateway = FakeGateway(content=_llm_json())
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=[_chunk("c1")]), gateway=gateway)
    agent.run(query="requirements?")
    assert len(gateway.calls) == 1


# --- ContextBuilder compatibility (§19.1/§19.3) ------------------------------


def test_citation_chunk_ids_match_context_evidence_ids() -> None:
    chunks = [
        _chunk("c1", score=0.9, title="Merit Policy"),
        _chunk("c2", score=0.7, title="Documents"),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c2", "c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="merit policy?")
    user_prompt = str(gateway.calls[0]["user_prompt"])
    cited_ids = {cit.chunk_id for cit in output.citations}
    for chunk in chunks:
        assert f"[chunk: {chunk.chunk_id}]" in user_prompt
        assert chunk.chunk_id in cited_ids


def test_citation_chunk_id_never_fabricated_beyond_evidence() -> None:
    chunks = [_chunk("c1", score=0.9)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert len(output.citations) == 1
    assert output.citations[0].chunk_id == "c1"
    assert len({cit.chunk_id for cit in output.citations} - {"c1"}) == 0


# --- Malformed / degenerate evidence ----------------------------------------


def test_duplicate_chunk_ids_in_retrieved_set_deterministic() -> None:
    chunks = [
        _chunk("c1", score=0.9, snippet="first"),
        _chunk("c1", score=0.8, snippet="second"),
    ]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    first = agent.run(query="requirements?").citations
    second = agent.run(query="requirements?").citations
    assert [cit.snippet for cit in first] == ["first"]
    assert [cit.snippet for cit in second] == ["first"]


def test_missing_optional_document_id_handled_safely() -> None:
    chunks = [_chunk("c1", score=0.9, document_id=None)]
    gateway = FakeGateway(content=_llm_json(cited_chunk_ids=["c1"]))
    agent = AdmissionAgent(retriever=FakeRetriever(chunks=chunks), gateway=gateway)
    output = agent.run(query="requirements?")
    assert output.status is WorkflowStatus.COMPLETED
    assert output.citations[0].document_id is None
    assert output.citations[0].chunk_id == "c1"


def test_empty_evidence_sequence_with_cited_ids_is_safe() -> None:
    agent = AdmissionAgent(
        retriever=FakeRetriever(chunks=[_chunk("c1")]),
        gateway=FakeGateway(content=_llm_json(cited_chunk_ids=["c1"])),
    )
    citations = agent.assemble_citations(chunks=[], cited_chunk_ids=["c1"])
    assert citations == []

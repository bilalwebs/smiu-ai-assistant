"""Concrete FAISS retriever tests (AI_ARCHITECTURE.md §16; IMPLEMENTATION_PLAN.md §4 RAG task 4).

Offline by construction: synthetic vectors, a deterministic fake embedding
provider, and in-memory ``VectorIndex`` instances — no Sentence Transformer
weights, no FAISS index in the repo tree, no network, no API keys
(TESTING_STRATEGY.md §12.1-12.4, §23.2). Covers the Phase 9 task 4
requirements: protocol conformance, query embedding integration, model parity,
dimension validation, FAISS search integration, top-K, score propagation,
deterministic ranking, padding/duplicate handling, ``RetrievedChunk``
conversion + metadata preservation, category + version-currency filtering,
typed error handling, the config-driven factory, and specialist compatibility.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from ai.agents.admission import AdmissionAgent
from ai.core.config import Settings
from ai.core.state import RetrievedChunk
from ai.gateway.base import LLMGateway, LLMResponse
from ai.rag.embeddings import ChunkEmbedding, EmbeddingProviderError
from ai.rag.faiss_index import (
    CorruptIndexError,
    FaissIndexError,
    FaissUnavailableError,
    IndexDimensionError,
    VectorIndex,
    build_index,
    save_index,
)
from ai.rag.faiss_retriever import (
    DimensionMismatchError,
    EmbeddingProviderUnavailableError,
    EmptyQueryError,
    FaissRetriever,
    IndexUnavailableError,
    InvalidQueryError,
    InvalidQueryVectorError,
    ModelParityError,
    QueryEmbeddingError,
    RetrieverError,
    SearchError,
    create_faiss_retriever,
)
from ai.rag.retriever import Retriever

MODEL_NAME = "fake/sentence-model"
QUERY_TEXT = "When is the admission deadline?"
QUERY_VECTOR = [0.8, 0.2, 0.0, 0.0]


class FakeEmbeddingProvider:
    """Deterministic, offline stand-in for a Sentence Transformer (§15.1).

    ``vectors`` overrides per-text output so tests can inject a fixed query
    vector, wrong-length vectors, zero-norm vectors, or non-finite vectors;
    ``embed_error`` simulates a failing provider. Vectors default to a stable
    SHA-256 digest so identical input always yields identical vectors.
    """

    def __init__(
        self,
        *,
        model_name: str = MODEL_NAME,
        dimension: int = 4,
        vectors: dict[str, list[float]] | None = None,
        embed_error: BaseException | None = None,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.vectors = vectors or {}
        self.embed_error = embed_error
        self.embed_calls: list[str] = []

    def _vector(self, text: str) -> list[float]:
        if text in self.vectors:
            return self.vectors[text]
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [float(digest[i % len(digest)]) / 255.0 for i in range(self.dimension)]

    def embed(self, *, text: str) -> list[float]:
        self.embed_calls.append(text)
        if self.embed_error is not None:
            raise self.embed_error
        return self._vector(text)

    def embed_batch(self, *, texts: Sequence[str]) -> list[list[float]]:
        if self.embed_error is not None:
            raise self.embed_error
        return [self._vector(text) for text in texts]


class FakeGateway(LLMGateway):
    """Scripted fake gateway so a specialist can be built offline."""

    def __init__(self, *, content: str = "{}") -> None:
        super().__init__(model="fake-model", max_retries=0)
        self.content = content

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
        return LLMResponse(content=self.content, model=model)


def make_embedding(
    chunk_id: str,
    vector: list[float],
    *,
    title: str = "Admission Policy",
    category: str = "admission",
    version: str = "1",
    source_path: str = "knowledge/admission/admission.md",
    chunk_index: int = 0,
    heading: str | None = None,
    document_id: uuid.UUID | None = None,
    model_name: str = MODEL_NAME,
    chunk_text: str | None = None,
) -> ChunkEmbedding:
    return ChunkEmbedding(
        chunk_id=chunk_id,
        document_id=document_id,
        title=title,
        category=category,
        version=version,
        source_path=source_path,
        chunk_index=chunk_index,
        heading=heading,
        model_name=model_name,
        chunk_text=chunk_text or f"{chunk_id} text.",
        vector=vector,
    )


def sample_embeddings() -> list[ChunkEmbedding]:
    """Deterministic 4-dim vectors across categories (§16.4 scope)."""
    return [
        make_embedding(
            "c1",
            [1.0, 0.0, 0.0, 0.0],
            chunk_index=0,
            heading="Eligibility",
            chunk_text="Applicants need 60% in intermediate to be eligible.",
        ),
        make_embedding(
            "c2",
            [0.0, 1.0, 0.0, 0.0],
            category="examination",
            title="Exam Policy",
            source_path="knowledge/examination/exam.md",
            chunk_index=0,
            chunk_text="Mid-term exams are held in week 8.",
        ),
        make_embedding(
            "c3",
            [0.5, 0.5, 0.0, 0.0],
            category="faq",
            title="University FAQ",
            source_path="knowledge/faq/faq.md",
            chunk_index=0,
            chunk_text="The registrar's office opens at 9am.",
        ),
        make_embedding(
            "c4",
            [-1.0, 0.0, 0.0, 0.0],
            chunk_index=1,
            heading="Transfers",
            chunk_text="Transfer applicants need 70%.",
        ),
    ]


def make_index(*, entries: list[ChunkEmbedding] | None = None) -> VectorIndex:
    return build_index(entries if entries is not None else sample_embeddings())


def make_provider(
    *, query_vector: list[float] = QUERY_VECTOR, **kwargs: object
) -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider(vectors={QUERY_TEXT: query_vector}, **kwargs)


def make_retriever(
    *,
    provider: FakeEmbeddingProvider | None = None,
    index: VectorIndex | None = None,
    **kwargs: object,
) -> FaissRetriever:
    return FaissRetriever(
        provider=provider if provider is not None else make_provider(),
        vector_index=index if index is not None else make_index(),
        **kwargs,
    )


def cosine_score(query: list[float], vector: list[float]) -> float:
    q = np.asarray(query, dtype=np.float64)
    v = np.asarray(vector, dtype=np.float64)
    return float(np.dot(q / np.linalg.norm(q), v / np.linalg.norm(v)))


# --- 1. Protocol conformance -----------------------------------------------


def test_concrete_retriever_satisfies_retriever_protocol() -> None:
    retriever = make_retriever()
    assert isinstance(retriever, Retriever)
    assert callable(retriever.retrieve)


# --- 2. Query embedding integration ----------------------------------------


def test_query_is_embedded_through_the_injected_provider() -> None:
    provider = make_provider()
    retriever = make_retriever(provider=provider)
    retriever.retrieve(query=QUERY_TEXT)
    assert provider.embed_calls == [QUERY_TEXT]


def test_query_and_index_share_the_embedding_model() -> None:
    index = make_index()
    provider = make_provider(model_name=MODEL_NAME, dimension=index.dimension)
    results = make_retriever(provider=provider, index=index).retrieve(query=QUERY_TEXT)
    assert results


def test_model_parity_mismatch_is_rejected() -> None:
    retriever = make_retriever(provider=make_provider(model_name="other/model"))
    with pytest.raises(ModelParityError):
        retriever.retrieve(query=QUERY_TEXT)


def test_dimension_parity_mismatch_is_rejected() -> None:
    retriever = make_retriever(provider=make_provider(dimension=3))
    with pytest.raises(DimensionMismatchError):
        retriever.retrieve(query=QUERY_TEXT)


def test_query_vector_dimension_mismatch_is_rejected() -> None:
    provider = make_provider(query_vector=[0.1, 0.2])
    retriever = make_retriever(provider=provider)
    with pytest.raises(DimensionMismatchError):
        retriever.retrieve(query=QUERY_TEXT)


# --- 3. FAISS search integration --------------------------------------------


def test_search_is_invoked_with_the_query_vector_and_full_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = make_index()
    calls: dict[str, object] = {}
    real_search = index.search

    def spy(*, vector: list[float], k: int) -> tuple[list[float], list[int]]:
        calls["vector"] = vector
        calls["k"] = k
        return real_search(vector=vector, k=k)

    monkeypatch.setattr(index, "search", spy)
    retriever = make_retriever(index=index)
    retriever.retrieve(query=QUERY_TEXT)
    assert calls["vector"] == QUERY_VECTOR
    assert calls["k"] == index.count


# --- 4. Top-K, scores, ranking, determinism ---------------------------------


def test_top_k_bounds_the_results() -> None:
    retriever = make_retriever()
    results = retriever.retrieve(query=QUERY_TEXT, top_k=2)
    assert len(results) == 2


def test_top_k_larger_than_index_returns_everything_without_padding() -> None:
    retriever = make_retriever()
    results = retriever.retrieve(query=QUERY_TEXT, top_k=10)
    assert len(results) == 4
    assert {chunk.chunk_id for chunk in results} == {"c1", "c2", "c3", "c4"}


def test_scores_are_raw_cosine_similarities_in_range() -> None:
    entries = sample_embeddings()
    retriever = make_retriever(index=make_index(entries=entries))
    results = retriever.retrieve(query=QUERY_TEXT, top_k=10)
    expected = {entry.chunk_id: cosine_score(QUERY_VECTOR, entry.vector) for entry in entries}
    for chunk in results:
        assert expected[chunk.chunk_id] == pytest.approx(chunk.score)
        assert -1.0 <= chunk.score <= 1.0


def test_ranking_is_score_descending() -> None:
    results = make_retriever().retrieve(query=QUERY_TEXT, top_k=10)
    assert [chunk.chunk_id for chunk in results] == ["c1", "c3", "c2", "c4"]
    assert results[0].score >= results[1].score >= results[2].score >= results[3].score


def test_equal_scores_tie_break_by_index_position() -> None:
    retriever = make_retriever(provider=make_provider(query_vector=[0.5, 0.5, 0.0, 0.0]))
    results = retriever.retrieve(query=QUERY_TEXT, top_k=10)
    assert [chunk.chunk_id for chunk in results] == ["c3", "c1", "c2", "c4"]
    assert results[1].score == pytest.approx(results[2].score)


def test_retrieval_is_deterministic() -> None:
    retriever = make_retriever()
    first = retriever.retrieve(query=QUERY_TEXT, top_k=3)
    second = retriever.retrieve(query=QUERY_TEXT, top_k=3)
    assert first == second


def test_duplicate_chunk_ids_are_deduplicated() -> None:
    import faiss

    base = faiss.IndexFlatIP(4)
    base.add(np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float32))
    entries = [
        make_embedding("dup", [1.0, 0.0, 0.0, 0.0]),
        make_embedding("dup", [0.0, 1.0, 0.0, 0.0]),
    ]
    index = VectorIndex(
        index=base,
        entries=entries,
        metric="cosine",
        model_name=MODEL_NAME,
        dimension=4,
    )
    retriever = make_retriever(
        provider=make_provider(query_vector=[1.0, 0.0, 0.0, 0.0]),
        index=index,
    )
    results = retriever.retrieve(query=QUERY_TEXT, top_k=10)
    assert len(results) == 1
    assert results[0].chunk_id == "dup"


# --- 5. RetrievedChunk conversion + metadata preservation --------------------


def test_retrieved_chunk_conversion_maps_all_contract_fields() -> None:
    doc_id = uuid.uuid4()
    entries = [
        make_embedding(
            "c1",
            [1.0, 0.0, 0.0, 0.0],
            document_id=doc_id,
            chunk_text="Applicants need 60%.",
            heading="Eligibility",
        )
    ]
    retriever = make_retriever(index=make_index(entries=entries))
    results = retriever.retrieve(query=QUERY_TEXT, top_k=10)
    assert len(results) == 1
    chunk = results[0]
    assert isinstance(chunk, RetrievedChunk)
    assert chunk.chunk_id == "c1"
    assert chunk.document_id == doc_id
    assert chunk.title == "Admission Policy"
    assert chunk.category == "admission"
    assert chunk.snippet == "Applicants need 60%."
    assert chunk.score == pytest.approx(cosine_score(QUERY_VECTOR, [1.0, 0.0, 0.0, 0.0]))


def test_rich_source_metadata_is_preserved_on_the_index_entries() -> None:
    doc_id = uuid.uuid4()
    entry = make_embedding(
        "c1",
        [1.0, 0.0, 0.0, 0.0],
        document_id=doc_id,
        version="2",
        source_path="knowledge/admission/policy.md",
        chunk_index=3,
        heading="Fees",
        chunk_text="Tuition is payable in two instalments.",
    )
    index = make_index(entries=[entry])
    results = make_retriever(index=index).retrieve(query=QUERY_TEXT, top_k=10)
    assert len(results) == 1
    assert results[0].snippet == "Tuition is payable in two instalments."
    kept = index.entries[0]
    assert kept.document_id == doc_id
    assert kept.version == "2"
    assert kept.source_path == "knowledge/admission/policy.md"
    assert kept.chunk_index == 3
    assert kept.heading == "Fees"
    assert kept.model_name == MODEL_NAME


# --- 6. Filtering: category + version currency -------------------------------


def test_category_filtering_narrows_to_specialist_scope() -> None:
    provider = make_provider(query_vector=[0.0, 1.0, 0.0, 0.0])
    retriever = make_retriever(provider=provider)
    results = retriever.retrieve(query=QUERY_TEXT, categories=("admission",), top_k=10)
    assert {chunk.chunk_id for chunk in results} == {"c1", "c4"}
    assert all(chunk.category == "admission" for chunk in results)


def test_category_filter_accepts_a_bare_string() -> None:
    provider = make_provider(query_vector=[0.0, 1.0, 0.0, 0.0])
    results = make_retriever(provider=provider).retrieve(
        query=QUERY_TEXT, categories="admission", top_k=10
    )
    assert {chunk.chunk_id for chunk in results} == {"c1", "c4"}


def test_category_filter_with_no_matches_returns_empty() -> None:
    results = make_retriever().retrieve(query=QUERY_TEXT, categories=("documents",), top_k=10)
    assert results == []


def test_stale_versions_are_excluded_when_current_versions_are_supplied() -> None:
    doc_a = uuid.uuid4()
    doc_b = uuid.uuid4()
    entries = [
        make_embedding("a1", [1.0, 0.0, 0.0, 0.0], document_id=doc_a, version="1"),
        make_embedding("a2", [0.8, 0.2, 0.0, 0.0], document_id=doc_a, version="2"),
        make_embedding("b1", [0.0, 1.0, 0.0, 0.0], document_id=doc_b, version="1"),
    ]
    retriever = make_retriever(
        index=make_index(entries=entries),
        current_versions={str(doc_a): "2"},
    )
    results = retriever.retrieve(query=QUERY_TEXT, top_k=10)
    chunk_ids = {chunk.chunk_id for chunk in results}
    assert "a2" in chunk_ids
    assert "a1" not in chunk_ids
    assert "b1" in chunk_ids


def test_version_currency_keys_by_title_when_document_id_is_absent() -> None:
    entries = [
        make_embedding("a1", [1.0, 0.0, 0.0, 0.0], version="1"),
        make_embedding("a2", [0.8, 0.2, 0.0, 0.0], version="2"),
    ]
    retriever = make_retriever(
        index=make_index(entries=entries),
        current_versions={"Admission Policy": "2"},
    )
    results = retriever.retrieve(query=QUERY_TEXT, top_k=10)
    assert {chunk.chunk_id for chunk in results} == {"a2"}


def test_documents_absent_from_current_versions_remain_eligible() -> None:
    retriever = make_retriever(current_versions={"Some Other Document": "99"})
    results = retriever.retrieve(query=QUERY_TEXT, top_k=10)
    assert len(results) == 4


# --- 7. Query validation -----------------------------------------------------


def test_empty_query_is_rejected() -> None:
    retriever = make_retriever()
    with pytest.raises(EmptyQueryError):
        retriever.retrieve(query="")
    with pytest.raises(EmptyQueryError):
        retriever.retrieve(query="   ")


def test_non_string_query_is_rejected() -> None:
    retriever = make_retriever()
    with pytest.raises(InvalidQueryError):
        retriever.retrieve(query=123)  # type: ignore[arg-type]


# --- 8. Missing/injected collaborators --------------------------------------


def test_missing_embedding_provider_raises_typed_error() -> None:
    retriever = FaissRetriever(vector_index=make_index())
    with pytest.raises(EmbeddingProviderUnavailableError):
        retriever.retrieve(query=QUERY_TEXT)


def test_missing_vector_index_raises_typed_error() -> None:
    retriever = FaissRetriever(provider=make_provider())
    with pytest.raises(IndexUnavailableError):
        retriever.retrieve(query=QUERY_TEXT)


def test_empty_index_returns_no_results() -> None:
    import faiss

    empty = VectorIndex(
        index=faiss.IndexFlatIP(4),
        entries=[],
        metric="cosine",
        model_name=MODEL_NAME,
        dimension=4,
    )
    results = make_retriever(index=empty).retrieve(query=QUERY_TEXT)
    assert results == []


# --- 9. Error propagation ----------------------------------------------------


def test_embedding_failure_is_propagated_as_query_embedding_error() -> None:
    retriever = make_retriever(provider=make_provider(embed_error=RuntimeError("boom")))
    with pytest.raises(QueryEmbeddingError):
        retriever.retrieve(query=QUERY_TEXT)


def test_provider_embedding_error_is_wrapped_as_query_embedding_error() -> None:
    retriever = make_retriever(
        provider=make_provider(embed_error=EmbeddingProviderError("model missing"))
    )
    with pytest.raises(QueryEmbeddingError):
        retriever.retrieve(query=QUERY_TEXT)


def test_zero_norm_query_vector_is_rejected() -> None:
    retriever = make_retriever(provider=make_provider(query_vector=[0.0, 0.0, 0.0, 0.0]))
    with pytest.raises(InvalidQueryVectorError):
        retriever.retrieve(query=QUERY_TEXT)


def test_non_finite_query_vector_is_rejected() -> None:
    retriever = make_retriever(provider=make_provider(query_vector=[float("nan"), 0.0, 0.0, 0.0]))
    with pytest.raises(InvalidQueryVectorError):
        retriever.retrieve(query=QUERY_TEXT)


def test_faiss_unavailable_search_failure_is_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    index = make_index()

    def broken(*, vector: list[float], k: int) -> tuple[list[float], list[int]]:
        raise FaissUnavailableError("faiss not installed")

    monkeypatch.setattr(index, "search", broken)
    retriever = make_retriever(index=index)
    with pytest.raises(SearchError):
        retriever.retrieve(query=QUERY_TEXT)


def test_generic_faiss_error_is_wrapped_as_search_error(monkeypatch: pytest.MonkeyPatch) -> None:
    index = make_index()

    def broken(*, vector: list[float], k: int) -> tuple[list[float], list[int]]:
        raise FaissIndexError("index exploded")

    monkeypatch.setattr(index, "search", broken)
    retriever = make_retriever(index=index)
    with pytest.raises(SearchError):
        retriever.retrieve(query=QUERY_TEXT)


def test_search_index_dimension_error_maps_to_dimension_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = make_index()

    def broken(*, vector: list[float], k: int) -> tuple[list[float], list[int]]:
        raise IndexDimensionError("dimension mismatch")

    monkeypatch.setattr(index, "search", broken)
    retriever = make_retriever(index=index)
    with pytest.raises(DimensionMismatchError):
        retriever.retrieve(query=QUERY_TEXT)


def test_out_of_range_search_position_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    index = make_index()

    def fake_search(*, vector: list[float], k: int) -> tuple[list[int], list[float]]:
        return ([5, 0], [0.9, 0.8])

    monkeypatch.setattr(index, "search", fake_search)
    retriever = make_retriever(index=index)
    with pytest.raises(SearchError):
        retriever.retrieve(query=QUERY_TEXT)


def test_negative_padding_position_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    index = make_index()

    def fake_search(*, vector: list[float], k: int) -> tuple[list[int], list[float]]:
        return ([-1], [0.9])

    monkeypatch.setattr(index, "search", fake_search)
    retriever = make_retriever(index=index)
    with pytest.raises(SearchError):
        retriever.retrieve(query=QUERY_TEXT)


def test_non_finite_search_score_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    index = make_index()

    def fake_search(*, vector: list[float], k: int) -> tuple[list[int], list[float]]:
        return ([0], [float("inf")])

    monkeypatch.setattr(index, "search", fake_search)
    retriever = make_retriever(index=index)
    with pytest.raises(SearchError):
        retriever.retrieve(query=QUERY_TEXT)


# --- 10. Configuration -------------------------------------------------------


def test_top_k_validation() -> None:
    retriever = make_retriever()
    with pytest.raises(ValueError):
        retriever.retrieve(query=QUERY_TEXT, top_k=0)
    with pytest.raises(ValueError):
        retriever.retrieve(query=QUERY_TEXT, top_k=-1)
    with pytest.raises(ValueError):
        FaissRetriever(provider=make_provider(), top_k=0)


# --- 11. Config-driven factory ----------------------------------------------


def test_factory_loads_a_persisted_index(tmp_path: Path) -> None:
    index = make_index()
    save_index(index, path=tmp_path)
    settings = Settings(embedding_model=MODEL_NAME, vector_store_path=str(tmp_path))
    retriever = create_faiss_retriever(
        settings,
        provider=make_provider(model_name=MODEL_NAME, dimension=index.dimension),
    )
    results = retriever.retrieve(query=QUERY_TEXT, top_k=10)
    assert len(results) == 4


def test_factory_honors_configured_top_k() -> None:
    settings = Settings(
        rag_top_k=2,
        embedding_model=MODEL_NAME,
        vector_store_path="knowledge/vectorstore",
    )
    retriever = create_faiss_retriever(
        settings,
        provider=make_provider(),
        vector_index=make_index(),
    )
    assert retriever.top_k == 2
    assert len(retriever.retrieve(query=QUERY_TEXT)) == 2


def test_factory_missing_index_raises_typed_error(tmp_path: Path) -> None:
    settings = Settings(embedding_model=MODEL_NAME, vector_store_path=str(tmp_path))
    with pytest.raises(IndexUnavailableError):
        create_faiss_retriever(settings, provider=make_provider())


def test_factory_corrupt_index_surfaces_precise_error(tmp_path: Path) -> None:
    index = make_index()
    save_index(index, path=tmp_path)
    (tmp_path / "index.faiss").write_bytes(b"not a faiss index")
    settings = Settings(embedding_model=MODEL_NAME, vector_store_path=str(tmp_path))
    with pytest.raises(CorruptIndexError):
        create_faiss_retriever(settings, provider=make_provider())


# --- 12. Specialist compatibility + offline guarantee -----------------------


def test_specialist_agent_accepts_the_concrete_retriever() -> None:
    retriever = make_retriever()
    agent = AdmissionAgent(retriever=retriever, gateway=FakeGateway())
    results = agent.retrieve(query="What are the admission requirements?")
    assert results
    assert all(chunk.category == "admission" for chunk in results)


def test_retrieval_runs_without_api_keys_or_network() -> None:
    retriever = make_retriever()
    results = retriever.retrieve(query=QUERY_TEXT, top_k=4)
    assert len(results) == 4
    assert all(isinstance(chunk, RetrievedChunk) for chunk in results)


def test_all_retriever_errors_share_a_typed_base() -> None:
    for error_type in (
        EmptyQueryError,
        InvalidQueryError,
        EmbeddingProviderUnavailableError,
        QueryEmbeddingError,
        InvalidQueryVectorError,
        DimensionMismatchError,
        ModelParityError,
        IndexUnavailableError,
        SearchError,
    ):
        assert issubclass(error_type, RetrieverError)

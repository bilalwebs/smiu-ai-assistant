"""Golden retrieval/eval set tests (IMPLEMENTATION_PLAN.md §4 RAG task 8).

Offline by construction: a deterministic fake ``EmbeddingProvider`` and tiny
designed corpora — no model weights, no network, no API keys, no database
(TESTING_STRATEGY.md §13.5, §23.2). Covers the versioned fixture schema,
ground-truth chunk-id integrity against the real ingestion pipeline,
``build_golden_index`` through the real pipeline, precision/recall scoring
with designed vectors, per-category gating (AI_ARCHITECTURE.md §38.1),
determinism, and the golden verifier used by the re-indexer's
verify-before-swap gate (TESTING_STRATEGY.md §13.5).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai.core.config import Settings
from ai.rag.evaluation import (
    DEFAULT_GOLDEN_SET_PATH,
    GoldenDocument,
    GoldenQuery,
    GoldenRetrievalSet,
    build_golden_index,
    build_golden_verifier,
    default_golden_set,
    evaluate_retrieval,
    golden_retriever_for_index,
    load_golden_set,
    precision_at_k,
    recall_at_k,
    verify_index_with_golden_set,
)
from ai.rag.faiss_index import index_exists, load_index
from ai.rag.ingestion import (
    DocumentChunk,
    KnowledgeCategory,
    KnowledgeIngestor,
    ingest_documents,
)
from ai.rag.reindexer import KnowledgeReindexer, ReindexVerificationError

FIXTURE_PATH = DEFAULT_GOLDEN_SET_PATH

MODEL_NAME = "fake/sentence-model"

DOC_ADMISSION = {
    "id": "doc-admission-gpa",
    "title": "Admission GPA Requirement",
    "category": "admission",
    "version": "1",
    "source_path": "admission/admission-gpa.md",
    "author": "Admissions Office",
    "text": "The university requires a minimum GPA of 2.5 for undergraduate admission.",
}
DOC_FEES = {
    "id": "doc-application-fee",
    "title": "Application Fee",
    "category": "admission",
    "version": "1",
    "source_path": "admission/application-fee.md",
    "author": "Admissions Office",
    "text": "The admission processing fee is paid online before the application deadline.",
}
DOC_HOURS = {
    "id": "doc-office-hours",
    "title": "Office Hours",
    "category": "faq",
    "version": "1",
    "source_path": "faq/office-hours.md",
    "author": "Registrar's Office",
    "text": "The registrar's office is open from 9:00 am to 5:00 pm on weekdays.",
}

QUERY_GPA_TEXT = "What GPA is required for undergraduate admission?"
QUERY_FEES_TEXT = "How is the admission processing fee paid?"
QUERY_HOURS_TEXT = "When is the registrar's office open?"

QUERY_GPA = {
    "id": "q-gpa",
    "query": QUERY_GPA_TEXT,
    "category": "admission",
    "expected_source": "admission/admission-gpa.md",
}
QUERY_FEES = {
    "id": "q-fees",
    "query": QUERY_FEES_TEXT,
    "category": "admission",
    "expected_source": "admission/application-fee.md",
}
QUERY_HOURS = {
    "id": "q-hours",
    "query": QUERY_HOURS_TEXT,
    "category": "faq",
    "expected_source": "faq/office-hours.md",
}

ADMISSION_VEC = [1.0, 0.0, 0.0, 0.0]
FEES_VEC = [0.0, 1.0, 0.0, 0.0]
HOURS_VEC = [0.0, 0.0, 1.0, 0.0]


class FakeEmbeddingProvider:
    """Deterministic, offline stand-in for a Sentence Transformer (§15.1)."""

    def __init__(
        self,
        *,
        model_name: str = MODEL_NAME,
        dimension: int = 4,
        vectors: dict[str, list[float]] | None = None,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.vectors: dict[str, list[float]] = dict(vectors or {})

    def _vector(self, text: str) -> list[float]:
        if text in self.vectors:
            return list(self.vectors[text])
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [float(digest[i % len(digest)]) / 255.0 for i in range(self.dimension)]

    def embed(self, *, text: str) -> list[float]:
        return self._vector(text)

    def embed_batch(self, *, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]


def designed_golden(
    documents: list[dict[str, str]],
    queries: list[dict[str, str | None]],
) -> tuple[GoldenRetrievalSet, dict[str, DocumentChunk]]:
    """Build a golden set whose expected ids come from the real pipeline.

    Returns ``(golden_set, by_source)`` where ``by_source`` maps a document's
    ``source_path`` to its ingested ``DocumentChunk``. The pipeline is
    deterministic, so the recorded ground-truth ids always match the chunks a
    re-index produces for the same sources and versions.
    """
    chunks = ingest_documents(list(documents))
    by_source = {chunk.source_path: chunk for doc in chunks for chunk in doc.chunks}
    built_queries: list[GoldenQuery] = []
    for raw in queries:
        current = dict(raw)
        source = current.pop("expected_source")
        expected = [by_source[str(source)].chunk_id] if source else []
        built_queries.append(
            GoldenQuery(
                id=str(current["id"]),
                query=str(current["query"]),
                category=str(current["category"]),
                expected_chunk_ids=expected,
            )
        )
    return (
        GoldenRetrievalSet(
            id="designed-v1",
            name="designed test corpus",
            version=1,
            description="deterministic test corpus",
            documents=[GoldenDocument(**dict(document)) for document in documents],
            queries=built_queries,
        ),
        by_source,
    )


def map_corpus_vectors(
    provider: FakeEmbeddingProvider,
    by_source: dict[str, DocumentChunk],
    mapping: dict[str, list[float]],
) -> None:
    """Map each chunk text to its designed embedding on the provider."""
    for source, vector in mapping.items():
        provider.vectors[by_source[source].chunk_text] = vector


def write_document(root: Path, source: str, category: str, body: str, *, title: str) -> Path:
    path = root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"---\ntitle: {title}\ncategory: {category}\nversion: 1\n---\n\n"
    path.write_text(header + body, encoding="utf-8")
    return path


# --- 1. Fixture schema and integrity ---------------------------------------


def test_fixture_loads_with_expected_structure() -> None:
    golden = load_golden_set(FIXTURE_PATH)
    assert golden.id == "golden-retrieval-v1"
    assert golden.version == 1
    assert len(golden.documents) == 6
    assert len(golden.queries) == 9

    query_ids = [query.id for query in golden.queries]
    assert len(query_ids) == len(set(query_ids))
    document_ids = [document.id for document in golden.documents]
    assert len(document_ids) == len(set(document_ids))


def test_default_golden_set_is_the_versioned_fixture() -> None:
    assert default_golden_set().model_dump() == load_golden_set(FIXTURE_PATH).model_dump()


def test_load_golden_set_raises_for_missing_path() -> None:
    with pytest.raises(FileNotFoundError):
        load_golden_set(Path("does-not-exist-golden.json"))


def test_fixture_rejects_unknown_version() -> None:
    payload = FIXTURE_PATH.read_text(encoding="utf-8")
    with pytest.raises(ValidationError):
        GoldenRetrievalSet.model_validate_json(
            payload.replace('"version": 1', '"version": 99')
        )


def test_fixture_covers_every_category_and_unanswerable_query() -> None:
    golden = load_golden_set(FIXTURE_PATH)
    assert {query.category for query in golden.queries} == set(KnowledgeCategory)
    assert {document.category for document in golden.documents} == set(KnowledgeCategory)
    unanswerable = next(query for query in golden.queries if query.id == "q-faq-scholarship")
    assert unanswerable.expected_chunk_ids == []


def test_fixture_ground_truth_ids_are_produced_by_pipeline() -> None:
    golden = load_golden_set(FIXTURE_PATH)
    chunks = ingest_documents(
        [
            {
                "text": document.text,
                "title": document.title,
                "category": document.category,
                "version": document.version,
                "source_path": document.source_path,
                "author": document.author,
            }
            for document in golden.documents
        ]
    )
    produced = {
        chunk.chunk_id for document in chunks for chunk in document.chunks
    }
    expected = {
        chunk_id for query in golden.queries for chunk_id in query.expected_chunk_ids
    }
    assert expected, "fixture must reference at least one ground-truth chunk"
    assert expected <= produced


# --- 2. build_golden_index --------------------------------------------------


def test_build_golden_index_builds_full_corpus_and_is_deterministic() -> None:
    golden, by_source = designed_golden(
        [DOC_ADMISSION, DOC_FEES, DOC_HOURS],
        [QUERY_GPA, QUERY_FEES, QUERY_HOURS],
    )
    provider = FakeEmbeddingProvider()

    index = build_golden_index(golden, provider=provider)
    again = build_golden_index(golden, provider=provider)

    assert index.count == len(by_source)
    assert index.model_name == provider.model_name
    assert index.dimension == provider.dimension
    assert index.count == again.count
    assert {entry.chunk_id for entry in index.entries} == {
        entry.chunk_id for entry in again.entries
    }


# --- 3. Metric helpers ------------------------------------------------------


def test_recall_and_precision_metric_helpers() -> None:
    assert recall_at_k(["a", "b"], ["a"]) == 1.0
    assert recall_at_k(["c"], ["a", "b"]) == 0.0
    assert recall_at_k([], []) == 1.0
    assert recall_at_k(["c"], []) == 0.0
    assert recall_at_k(["a"], ["a"]) == 1.0

    assert precision_at_k(["a", "x"], ["a", "b"]) == 0.5
    assert precision_at_k([], ["a"]) == 0.0
    assert precision_at_k(["a"], []) == 0.0
    assert precision_at_k(["a", "b"], ["a", "b"]) == 1.0


# --- 4. evaluate_retrieval --------------------------------------------------


def test_evaluate_retrieval_passes_on_designed_corpus() -> None:
    golden, by_source = designed_golden(
        [DOC_ADMISSION, DOC_HOURS],
        [QUERY_GPA, QUERY_HOURS],
    )
    provider = FakeEmbeddingProvider()
    map_corpus_vectors(
        provider,
        by_source,
        {
            "admission/admission-gpa.md": ADMISSION_VEC,
            "faq/office-hours.md": HOURS_VEC,
        },
    )
    provider.vectors[QUERY_GPA_TEXT] = ADMISSION_VEC
    provider.vectors[QUERY_HOURS_TEXT] = HOURS_VEC

    index = build_golden_index(golden, provider=provider)
    retriever = golden_retriever_for_index(index, provider=provider)
    result = evaluate_retrieval(retriever, golden, top_k=4)

    assert result.golden_set_id == "designed-v1"
    assert result.mean_recall_at_k == 1.0
    assert result.mean_precision_at_k == 1.0
    assert result.passed is True
    assert all(item.hit for item in result.queries)


def test_evaluate_retrieval_scopes_queries_to_their_category() -> None:
    golden, by_source = designed_golden(
        [DOC_ADMISSION, DOC_HOURS],
        [QUERY_GPA, QUERY_HOURS],
    )
    provider = FakeEmbeddingProvider()
    map_corpus_vectors(
        provider,
        by_source,
        {
            "admission/admission-gpa.md": ADMISSION_VEC,
            "faq/office-hours.md": ADMISSION_VEC,
        },
    )
    provider.vectors[QUERY_GPA_TEXT] = ADMISSION_VEC
    provider.vectors[QUERY_HOURS_TEXT] = ADMISSION_VEC

    index = build_golden_index(golden, provider=provider)
    retriever = golden_retriever_for_index(index, provider=provider)
    result = evaluate_retrieval(retriever, golden, top_k=4)

    admissions = next(item for item in result.queries if item.query_id == "q-gpa")
    hours = next(item for item in result.queries if item.query_id == "q-hours")
    assert admissions.retrieved_chunk_ids == [
        by_source["admission/admission-gpa.md"].chunk_id
    ]
    assert hours.retrieved_chunk_ids == [by_source["faq/office-hours.md"].chunk_id]
    assert hours.recall_at_k == 1.0


def test_evaluate_retrieval_fails_when_ground_truth_is_missed() -> None:
    golden, by_source = designed_golden(
        [DOC_ADMISSION, DOC_FEES],
        [QUERY_GPA],
    )
    provider = FakeEmbeddingProvider()
    map_corpus_vectors(
        provider,
        by_source,
        {
            "admission/admission-gpa.md": ADMISSION_VEC,
            "admission/application-fee.md": FEES_VEC,
        },
    )
    provider.vectors[QUERY_GPA_TEXT] = FEES_VEC

    index = build_golden_index(golden, provider=provider)
    retriever = golden_retriever_for_index(index, provider=provider)
    result = evaluate_retrieval(retriever, golden, top_k=1)

    assert result.mean_recall_at_k == 0.0
    assert result.passed is False
    assert result.queries[0].hit is False


def test_evaluate_retrieval_enforces_the_per_category_gate() -> None:
    golden, by_source = designed_golden(
        [DOC_ADMISSION, DOC_FEES, DOC_HOURS],
        [
            dict(QUERY_GPA),
            dict(QUERY_FEES),
            dict(QUERY_HOURS),
            {
                "id": "q-hours-b",
                "query": "When is the office open today?",
                "category": "faq",
                "expected_source": "faq/office-hours.md",
            },
            {
                "id": "q-hours-c",
                "query": "What are the office hours?",
                "category": "faq",
                "expected_source": "faq/office-hours.md",
            },
        ],
    )
    provider = FakeEmbeddingProvider()
    map_corpus_vectors(
        provider,
        by_source,
        {
            "admission/admission-gpa.md": ADMISSION_VEC,
            "admission/application-fee.md": FEES_VEC,
            "faq/office-hours.md": HOURS_VEC,
        },
    )
    provider.vectors[QUERY_GPA_TEXT] = FEES_VEC
    provider.vectors[QUERY_FEES_TEXT] = ADMISSION_VEC
    provider.vectors[QUERY_HOURS_TEXT] = HOURS_VEC
    provider.vectors["When is the office open today?"] = HOURS_VEC
    provider.vectors["What are the office hours?"] = HOURS_VEC

    index = build_golden_index(golden, provider=provider)
    retriever = golden_retriever_for_index(index, provider=provider)
    result = evaluate_retrieval(retriever, golden, top_k=1)

    assert result.mean_recall_at_k == 0.6
    assert result.mean_precision_at_k == 0.6
    assert result.passed is False
    admission_summary = next(
        item for item in result.categories if item.category == "admission"
    )
    faq_summary = next(item for item in result.categories if item.category == "faq")
    assert admission_summary.mean_recall_at_k == 0.0
    assert admission_summary.recall_pass is False
    assert faq_summary.mean_recall_at_k == 1.0
    assert faq_summary.recall_pass is True


def test_evaluate_retrieval_unanswerable_query_scores_as_expected() -> None:
    golden, by_source = designed_golden(
        [DOC_ADMISSION],
        [
            {
                "id": "q-scholarship",
                "query": "What is the minimum GPA for the scholarship program?",
                "category": "faq",
                "expected_source": None,
            }
        ],
    )
    provider = FakeEmbeddingProvider()
    map_corpus_vectors(
        provider, by_source, {"admission/admission-gpa.md": ADMISSION_VEC}
    )

    index = build_golden_index(golden, provider=provider)
    retriever = golden_retriever_for_index(index, provider=provider)
    result = evaluate_retrieval(retriever, golden, top_k=4)

    query = result.queries[0]
    assert query.retrieved_chunk_ids == []
    assert query.recall_at_k == 1.0
    assert query.precision_at_k == 0.0
    assert query.hit is False
    assert result.passed is False


def test_evaluate_retrieval_is_deterministic() -> None:
    golden, by_source = designed_golden(
        [DOC_ADMISSION, DOC_HOURS],
        [QUERY_GPA, QUERY_HOURS],
    )
    provider = FakeEmbeddingProvider()
    map_corpus_vectors(
        provider,
        by_source,
        {
            "admission/admission-gpa.md": ADMISSION_VEC,
            "faq/office-hours.md": HOURS_VEC,
        },
    )
    provider.vectors[QUERY_GPA_TEXT] = ADMISSION_VEC
    provider.vectors[QUERY_HOURS_TEXT] = HOURS_VEC
    index = build_golden_index(golden, provider=provider)
    retriever = golden_retriever_for_index(index, provider=provider)

    first = evaluate_retrieval(retriever, golden, top_k=4)
    second = evaluate_retrieval(retriever, golden, top_k=4)

    assert first.model_dump() == second.model_dump()


# --- 5. Golden verifier -----------------------------------------------------


def test_verify_index_with_golden_set_and_build_golden_verifier() -> None:
    golden, by_source = designed_golden(
        [DOC_ADMISSION, DOC_FEES, DOC_HOURS],
        [QUERY_GPA, QUERY_FEES, QUERY_HOURS],
    )
    good = FakeEmbeddingProvider()
    map_corpus_vectors(
        good,
        by_source,
        {
            "admission/admission-gpa.md": ADMISSION_VEC,
            "admission/application-fee.md": FEES_VEC,
            "faq/office-hours.md": HOURS_VEC,
        },
    )
    good.vectors[QUERY_GPA_TEXT] = ADMISSION_VEC
    good.vectors[QUERY_FEES_TEXT] = FEES_VEC
    good.vectors[QUERY_HOURS_TEXT] = HOURS_VEC

    good_index = build_golden_index(golden, provider=good)
    assert (
        verify_index_with_golden_set(good_index, provider=good, golden_set=golden, top_k=1)
        is True
    )
    verifier = build_golden_verifier(good, golden, top_k=1)
    assert verifier(good_index) is True

    bad = FakeEmbeddingProvider()
    bad.vectors[by_source["admission/admission-gpa.md"].chunk_text] = ADMISSION_VEC
    bad.vectors[by_source["admission/application-fee.md"].chunk_text] = FEES_VEC
    bad.vectors[by_source["faq/office-hours.md"].chunk_text] = HOURS_VEC
    bad.vectors[QUERY_GPA_TEXT] = FEES_VEC
    bad.vectors[QUERY_FEES_TEXT] = ADMISSION_VEC
    bad.vectors[QUERY_HOURS_TEXT] = HOURS_VEC

    bad_index = build_golden_index(golden, provider=bad)
    assert (
        verify_index_with_golden_set(bad_index, provider=bad, golden_set=golden, top_k=1)
        is False
    )
    assert build_golden_verifier(bad, golden, top_k=1)(bad_index) is False


# --- 6. Re-indexer integration (verify-before-swap gate) --------------------


def test_reindexer_swaps_only_when_golden_set_verifies(tmp_path: Path) -> None:
    good_root = tmp_path / "good"
    write_document(
        good_root,
        "faq/admission-gpa.md",
        "faq",
        DOC_ADMISSION["text"],
        title="Admission GPA Requirement",
    )
    write_document(
        good_root, "faq/office-hours.md", "faq", DOC_HOURS["text"], title="Office Hours"
    )
    good_provider = FakeEmbeddingProvider()
    good_golden, _ = _faq_golden(good_root, good_provider, swap_queries=False)

    good_reindexer = KnowledgeReindexer(
        settings=_settings(good_root),
        ingestor=KnowledgeIngestor(good_root),
        provider=good_provider,
        verify_before_swap=build_golden_verifier(good_provider, good_golden, top_k=1),
    )
    report = good_reindexer.run()

    assert report.status == "completed"
    assert report.index_count == 2
    assert load_index(path=_settings(good_root).vector_store_path).count == 2

    bad_root = tmp_path / "bad"
    write_document(
        bad_root,
        "faq/admission-gpa.md",
        "faq",
        DOC_ADMISSION["text"],
        title="Admission GPA Requirement",
    )
    write_document(
        bad_root, "faq/office-hours.md", "faq", DOC_HOURS["text"], title="Office Hours"
    )
    bad_provider = FakeEmbeddingProvider()
    bad_golden, _ = _faq_golden(bad_root, bad_provider, swap_queries=True)

    bad_reindexer = KnowledgeReindexer(
        settings=_settings(bad_root),
        ingestor=KnowledgeIngestor(bad_root),
        provider=bad_provider,
        verify_before_swap=build_golden_verifier(bad_provider, bad_golden, top_k=1),
    )
    with pytest.raises(ReindexVerificationError):
        bad_reindexer.run()
    assert not index_exists(path=_settings(bad_root).vector_store_path)


def _faq_golden(
    root: Path,
    provider: FakeEmbeddingProvider,
    *,
    swap_queries: bool,
) -> tuple[GoldenRetrievalSet, dict[str, DocumentChunk]]:
    """Golden set over the two faq docs; expected ids from the real ingestor."""
    ingested = KnowledgeIngestor(root).ingest_directory()
    by_source = {chunk.source_path: chunk for doc in ingested for chunk in doc.chunks}

    provider.vectors[by_source["faq/admission-gpa.md"].chunk_text] = ADMISSION_VEC
    provider.vectors[by_source["faq/office-hours.md"].chunk_text] = HOURS_VEC
    if swap_queries:
        provider.vectors[QUERY_GPA_TEXT] = HOURS_VEC
        provider.vectors[QUERY_HOURS_TEXT] = ADMISSION_VEC
    else:
        provider.vectors[QUERY_GPA_TEXT] = ADMISSION_VEC
        provider.vectors[QUERY_HOURS_TEXT] = HOURS_VEC

    golden = GoldenRetrievalSet(
        id="faq-verifier-v1",
        name="faq verifier corpus",
        version=1,
        documents=[
            GoldenDocument(
                id="doc-admission-gpa",
                title="Admission GPA Requirement",
                category="faq",
                version="1",
                source_path="faq/admission-gpa.md",
                author="Admissions Office",
                text=DOC_ADMISSION["text"],
            ),
            GoldenDocument(
                id="doc-office-hours",
                title="Office Hours",
                category="faq",
                version="1",
                source_path="faq/office-hours.md",
                author="Registrar's Office",
                text=DOC_HOURS["text"],
            ),
        ],
        queries=[
            GoldenQuery(
                id="q-gpa",
                query=QUERY_GPA_TEXT,
                category="faq",
                expected_chunk_ids=[by_source["faq/admission-gpa.md"].chunk_id],
            ),
            GoldenQuery(
                id="q-hours",
                query=QUERY_HOURS_TEXT,
                category="faq",
                expected_chunk_ids=[by_source["faq/office-hours.md"].chunk_id],
            ),
        ],
    )
    return golden, by_source


def _settings(root: Path) -> Settings:
    return Settings(
        knowledge_root=str(root / "knowledge"),
        vector_store_path=str(root / "vectorstore"),
        embedding_model=MODEL_NAME,
        _env_file=None,
    )

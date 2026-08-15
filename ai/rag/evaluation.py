"""Golden retrieval/eval sets and regression harness (IMPLEMENTATION_PLAN.md §4 RAG task 8).

Purpose:
    Establish versioned golden retrieval sets and a deterministic evaluation
    harness that measures retrieval accuracy (AI_ARCHITECTURE.md §38.1) so
    retrieval quality is regression-tested after every ingestion, chunking, or
    embedding change and before an index swap (TESTING_STRATEGY.md §12.1-12.3,
    §13.5-13.6).

Golden retrieval set (AI_ARCHITECTURE.md §38.1; TESTING_STRATEGY.md §12.2):
    A ground-truth set of (query, expected relevant chunk ids) pairs plus the
    corpus those ids refer to. ``expected_chunk_ids`` are the deterministic
    sha256 chunk ids the Phase 9 ingestion pipeline produces (AI_ARCHITECTURE.md
    §36.4) — the fixture's ids are regenerated only when chunking changes, and
    regeneration is validated against retrieval (TESTING_STRATEGY.md §12.3,
    §13.6). The default fixture lives at ``ai/tests/golden/retrieval/
    golden_retrieval_v1.json`` and covers every knowledge category plus an
    information-unavailable query (TESTING_STRATEGY.md §12.6).

Harness (AI_ARCHITECTURE.md §38.1-38.2):
    ``evaluate_retrieval`` runs a golden set through any injected ``Retriever``
    and scores each query with retrieval precision/recall at top-K, aggregates
    overall and per-category metrics, and reports a boolean pass/fail against
    configurable thresholds. ``build_golden_index`` builds a ``VectorIndex``
    from a golden set's corpus through the real ingestion → embedding → index
    pipeline, so the harness regresses against ingestion, chunking, and
    embedding changes together, not just the retriever.

Determinism:
    The harness performs no randomness, timing, or external calls. Given the
    same retriever, golden set, and thresholds it returns identical results.

Offline by construction:
    No model weights, network, API keys, or database are required. The harness
    is provider-agnostic: tests inject a deterministic fake ``EmbeddingProvider``
    and real embeddings are used only in production regression runs.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from ai.rag.embeddings import EmbeddingProvider, EmbeddingService
from ai.rag.faiss_index import VectorIndex, build_index
from ai.rag.faiss_retriever import FaissRetriever
from ai.rag.ingestion import KnowledgeCategory, ingest_documents
from ai.rag.retriever import Retriever

# Version of the on-disk golden retrieval set format. Bump when the JSON schema
# changes; loaders reject an unknown version.
GOLDEN_SET_VERSION = 1
# Default fixture location (ai/tests/golden/retrieval/).
DEFAULT_GOLDEN_SET_PATH = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "golden"
    / "retrieval"
    / "golden_retrieval_v1.json"
)

# Default evaluation thresholds. AI_ARCHITECTURE.md §38.1 keeps retrieval
# accuracy targets "high; tracked per category" and does not mandate numbers,
# so these are configurable harness defaults, not architecture constants.
DEFAULT_RECALL_THRESHOLD = 0.5
DEFAULT_PRECISION_THRESHOLD = 0.25
DEFAULT_PER_CATEGORY_THRESHOLD = 0.5


class GoldenQuery(BaseModel):
    """One ground-truth retrieval query (AI_ARCHITECTURE.md §38.1)."""

    id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    category: str = Field(min_length=1)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    note: str | None = None

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        try:
            return KnowledgeCategory(value).value
        except ValueError as exc:
            raise ValueError(
                f"unknown golden query category {value!r}; expected one of "
                f"{', '.join(category.value for category in KnowledgeCategory)}"
            ) from exc


class GoldenDocument(BaseModel):
    """One corpus document in a golden retrieval set (§36.2, §36.5)."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1)
    version: str = Field(min_length=1, max_length=30)
    source_path: str = Field(min_length=1)
    author: str | None = None
    text: str = Field(min_length=1)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        try:
            return KnowledgeCategory(value).value
        except ValueError as exc:
            raise ValueError(
                f"unknown golden document category {value!r}; expected one of "
                f"{', '.join(category.value for category in KnowledgeCategory)}"
            ) from exc


class GoldenRetrievalSet(BaseModel):
    """A versioned, validated golden retrieval set (§38.1, §12.2)."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: int = GOLDEN_SET_VERSION
    description: str | None = None
    documents: list[GoldenDocument]
    queries: list[GoldenQuery]

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: int) -> int:
        if value != GOLDEN_SET_VERSION:
            raise ValueError(
                f"golden retrieval set version {value} is not supported "
                f"(expected {GOLDEN_SET_VERSION})"
            )
        return value


class QueryEvaluation(BaseModel):
    """Retrieval metrics for a single golden query (§38.1)."""

    query_id: str
    query: str
    category: str
    expected_chunk_ids: list[str]
    retrieved_chunk_ids: list[str]
    hits: list[str]
    recall_at_k: float
    precision_at_k: float
    hit: bool


class CategorySummary(BaseModel):
    """Aggregated retrieval metrics for one knowledge category (§38.1)."""

    category: str
    queries: int
    mean_recall_at_k: float
    mean_precision_at_k: float
    recall_pass: bool
    precision_pass: bool


class RetrievalEvaluation(BaseModel):
    """The complete evaluation of a golden set against a retriever (§38)."""

    golden_set_id: str
    golden_set_version: int
    top_k: int
    recall_threshold: float
    precision_threshold: float
    per_category_threshold: float
    queries: list[QueryEvaluation]
    categories: list[CategorySummary]
    mean_recall_at_k: float
    mean_precision_at_k: float
    passed: bool


def load_golden_set(path: str | Path) -> GoldenRetrievalSet:
    """Load and validate a golden retrieval set from ``path``."""
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"golden retrieval set not found: {target}")
    payload = target.read_text(encoding="utf-8")
    return GoldenRetrievalSet.model_validate_json(payload)


def default_golden_set() -> GoldenRetrievalSet:
    """Load the versioned default golden retrieval set fixture."""
    return load_golden_set(DEFAULT_GOLDEN_SET_PATH)


def build_golden_index(
    golden_set: GoldenRetrievalSet,
    *,
    provider: EmbeddingProvider,
    chunk_size: int = 800,
    overlap: int = 80,
) -> VectorIndex:
    """Build a ``VectorIndex`` from a golden set corpus through the real pipeline.

    The corpus runs through the Phase 9 ingestion → embedding → index pipeline
    (tasks 1-3) so the harness regresses against ingestion, chunking, and
    embedding changes together (TESTING_STRATEGY.md §12.2, §13.6). Chunk ids are
    therefore exactly the deterministic ids recorded as ground truth in the set.
    """
    ingested = ingest_documents(
        [
            {
                "text": document.text,
                "title": document.title,
                "category": document.category,
                "version": document.version,
                "source_path": document.source_path,
                "author": document.author,
                "file_type": "md",
            }
            for document in golden_set.documents
        ],
        chunk_size=chunk_size,
        overlap=overlap,
    )
    chunks = [chunk for document in ingested for chunk in document.chunks]
    embeddings = EmbeddingService(provider=provider).embed_chunks(chunks)
    return build_index(embeddings)


def golden_retriever_for_index(
    index: VectorIndex,
    *,
    provider: EmbeddingProvider,
    top_k: int = 4,
) -> FaissRetriever:
    """Build a retriever over a candidate index for evaluation (§16.5)."""
    return FaissRetriever(provider=provider, vector_index=index, top_k=top_k)


def recall_at_k(retrieved: list[str], expected: list[str]) -> float:
    """Retrieval recall@k — the share of expected chunks that were retrieved.

    A query with no expected chunks scores recall 1.0 when nothing was retrieved
    (correctly surfaced as information-unavailable, §12.6) and 0.0 when
    unrelated chunks were returned.
    """
    expected_set = set(expected)
    retrieved_set = set(retrieved)
    if not expected_set:
        return 1.0 if not retrieved_set else 0.0
    return len(expected_set & retrieved_set) / len(expected_set)


def precision_at_k(retrieved: list[str], expected: list[str]) -> float:
    """Retrieval precision@k — the share of retrieved chunks that are relevant.

    When nothing was retrieved the precision is 0.0 (no useful result); with
    expected chunks empty and a non-empty retrieval it is likewise 0.0.
    """
    if not retrieved:
        return 0.0
    expected_set = set(expected)
    return len(expected_set & set(retrieved)) / len(retrieved)


def evaluate_retrieval(
    retriever: Retriever,
    golden_set: GoldenRetrievalSet,
    *,
    top_k: int = 4,
    recall_threshold: float = DEFAULT_RECALL_THRESHOLD,
    precision_threshold: float = DEFAULT_PRECISION_THRESHOLD,
    per_category_threshold: float = DEFAULT_PER_CATEGORY_THRESHOLD,
) -> RetrievalEvaluation:
    """Evaluate a golden set against a retriever and score retrieval accuracy.

    Each golden query is retrieved (scoped to its category, bounded by
    ``top_k``) and scored with precision/recall@k against the ground truth. The
    evaluation passes only when the overall mean recall and precision meet
    their thresholds AND every non-empty category's mean recall meets the
    per-category threshold (AI_ARCHITECTURE.md §38.1 — accuracy tracked per
    category).
    """
    if top_k <= 0:
        raise ValueError("top_k must be a positive integer")

    per_query: list[QueryEvaluation] = []
    for golden in golden_set.queries:
        retrieved = retriever.retrieve(
            query=golden.query, categories=(golden.category,), top_k=top_k
        )
        retrieved_ids = [chunk.chunk_id for chunk in retrieved]
        expected = list(golden.expected_chunk_ids)
        hits = [
            chunk_id for chunk_id in retrieved_ids if chunk_id in set(expected)
        ]
        per_query.append(
            QueryEvaluation(
                query_id=golden.id,
                query=golden.query,
                category=golden.category,
                expected_chunk_ids=expected,
                retrieved_chunk_ids=retrieved_ids,
                hits=hits,
                recall_at_k=recall_at_k(retrieved_ids, expected),
                precision_at_k=precision_at_k(retrieved_ids, expected),
                hit=bool(hits),
            )
        )

    per_category = _category_summaries(per_query, per_category_threshold)
    mean_recall = _mean([item.recall_at_k for item in per_query])
    mean_precision = _mean([item.precision_at_k for item in per_query])

    passed = (
        mean_recall >= recall_threshold
        and mean_precision >= precision_threshold
        and all(item.recall_pass for item in per_category)
        and all(item.precision_pass for item in per_category)
    )

    return RetrievalEvaluation(
        golden_set_id=golden_set.id,
        golden_set_version=golden_set.version,
        top_k=top_k,
        recall_threshold=recall_threshold,
        precision_threshold=precision_threshold,
        per_category_threshold=per_category_threshold,
        queries=per_query,
        categories=per_category,
        mean_recall_at_k=mean_recall,
        mean_precision_at_k=mean_precision,
        passed=passed,
    )


def verify_index_with_golden_set(
    index: VectorIndex,
    *,
    provider: EmbeddingProvider,
    golden_set: GoldenRetrievalSet,
    top_k: int = 4,
    recall_threshold: float = DEFAULT_RECALL_THRESHOLD,
    precision_threshold: float = DEFAULT_PRECISION_THRESHOLD,
    per_category_threshold: float = DEFAULT_PER_CATEGORY_THRESHOLD,
) -> bool:
    """True when a candidate index satisfies a golden retrieval set.

    The regression gate for index regeneration (TESTING_STRATEGY.md §13.5):
    an index is safe to swap only when retrieval over it still satisfies the
    golden set. Embedding drift on a model change surfaces here as a failed
    verification (TESTING_STRATEGY.md §12.2).
    """
    retriever = golden_retriever_for_index(index, provider=provider, top_k=top_k)
    evaluation = evaluate_retrieval(
        retriever,
        golden_set,
        top_k=top_k,
        recall_threshold=recall_threshold,
        precision_threshold=precision_threshold,
        per_category_threshold=per_category_threshold,
    )
    return evaluation.passed


def build_golden_verifier(
    provider: EmbeddingProvider,
    golden_set: GoldenRetrievalSet,
    *,
    top_k: int = 4,
    recall_threshold: float = DEFAULT_RECALL_THRESHOLD,
    precision_threshold: float = DEFAULT_PRECISION_THRESHOLD,
    per_category_threshold: float = DEFAULT_PER_CATEGORY_THRESHOLD,
) -> Callable[[VectorIndex], bool]:
    """Build a ``verify_before_swap`` callable for the re-indexer (task 7).

    The returned function verifies a candidate ``VectorIndex`` against the
    golden set before the re-indexer atomically swaps it in
    (AI_ARCHITECTURE.md §36.7 atomic swap; TESTING_STRATEGY.md §13.5).
    """
    return lambda index: verify_index_with_golden_set(
        index,
        provider=provider,
        golden_set=golden_set,
        top_k=top_k,
        recall_threshold=recall_threshold,
        precision_threshold=precision_threshold,
        per_category_threshold=per_category_threshold,
    )


def _category_summaries(
    results: list[QueryEvaluation],
    per_category_threshold: float,
) -> list[CategorySummary]:
    """Aggregate per-query metrics into per-category summaries (§38.1)."""
    grouped: dict[str, list[QueryEvaluation]] = {}
    for item in results:
        grouped.setdefault(item.category, []).append(item)

    summaries: list[CategorySummary] = []
    for category in sorted(grouped):
        items = grouped[category]
        mean_recall = _mean([item.recall_at_k for item in items])
        mean_precision = _mean([item.precision_at_k for item in items])
        summaries.append(
            CategorySummary(
                category=category,
                queries=len(items),
                mean_recall_at_k=mean_recall,
                mean_precision_at_k=mean_precision,
                recall_pass=mean_recall >= per_category_threshold,
                precision_pass=mean_precision >= per_category_threshold,
            )
        )
    return summaries


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    total = sum(values)
    return total / len(values)


# Public API of the golden retrieval-set evaluation harness.
__all__ = [
    "DEFAULT_GOLDEN_SET_PATH",
    "CategorySummary",
    "GoldenDocument",
    "GoldenQuery",
    "GoldenRetrievalSet",
    "QueryEvaluation",
    "RetrievalEvaluation",
    "build_golden_index",
    "build_golden_verifier",
    "default_golden_set",
    "evaluate_retrieval",
    "golden_retriever_for_index",
    "load_golden_set",
    "precision_at_k",
    "recall_at_k",
    "verify_index_with_golden_set",
]

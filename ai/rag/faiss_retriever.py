"""Concrete FAISS-backed retriever (AI_ARCHITECTURE.md §16; IMPLEMENTATION_PLAN.md §4 RAG task 4).

Purpose:
    The Phase 9 task 4 concrete implementation of the ``Retriever`` protocol
    (ai/rag/retriever.py). It owns retrieval orchestration only:

        query → EmbeddingProvider (task 2) → VectorIndex.search (task 3)
        → §16.4 filtering → deterministic ranking → RetrievedChunk[] (§19.1)

    Everything else — document ingestion, chunking, the embedding-model
    implementation, FAISS persistence, ContextBuilder, citation assembly, and
    LLM generation — is owned by tasks 1-3 and 5-6 and is deliberately absent.

Retrieval policy (AI_ARCHITECTURE.md §14.3, §16):
    - Query embedding: the query is embedded with the same model as the corpus
      through the injected task-2 ``EmbeddingProvider`` (via
      ``EmbeddingService.embed_query``). Model parity (§15.1) is enforced
      against the index's recorded model and dimension (§15.2 bookkeeping): a
      provider whose model or dimension differs from the index raises a typed
      error instead of silently searching a mismatched vector space.
    - Search: ``VectorIndex.search`` returns raw cosine similarities in [-1, 1]
      in descending order, with FAISS ``-1`` padding already dropped (task 3).
      The retriever searches the full candidate pool (``IndexFlatIP`` is an
      exhaustive scan, so this is no more expensive than a small ``k``) and then
      filters — the protocol requires "top ``top_k`` chunks ... already filtered
      by document status/version and scoped to the requested categories".
    - Filtering (§16.4): category scoping from the ``categories`` argument; the
      index itself is built only from ``is_active`` + ``status='processed'``
      current-version documents (a Phase 9 task 7 / backend indexer concern per
      §21.3, not a per-query DB layer), and version currency is additionally
      enforced against the injected ``current_versions`` map when the caller
      supplies the DB-owned "current version" state (DATABASE_DESIGN.md §21.3).
    - Ranking (§16.3): primary = raw cosine score, descending; ties break
      deterministically by index position (input order) — the architecture's
      recency/priority tie-break metadata is a Phase 2 / DB concern absent from
      the persisted index, so position order is the deterministic fallback.
    - Top-K (§16.5): the top ``top_k`` eligible hits, never more. AI_ARCHITECTURE.md
      §16 defines no similarity threshold, so none is invented here.

Determinism: for identical (query, index, embedding provider, configuration)
the same ordered results are returned — hits are sorted by ``(-score,
position)`` and no randomness, time, or external state participates.

Error handling: every failure raises a typed ``RetrieverError`` (empty/invalid
query, missing provider or index, embedding/provider failure, model-parity or
dimension mismatch, invalid query vector, failed/corrupt search result,
``RetrievedChunk`` conversion). The retriever never silently returns unrelated
results and never silently builds a new index.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path

from ai.core.config import Settings
from ai.core.state import RetrievedChunk
from ai.rag.embeddings import (
    ChunkEmbedding,
    EmbeddingError,
    EmbeddingProvider,
    EmbeddingService,
    EmptyEmbeddingInputError,
    EmptyVectorError,
    create_embedding_provider,
)
from ai.rag.embeddings import (
    DimensionMismatchError as EmbeddingDimensionMismatchError,
)
from ai.rag.embeddings import (
    InvalidVectorError as EmbeddingInvalidVectorError,
)
from ai.rag.faiss_index import (
    FaissIndexError,
    FaissUnavailableError,
    IndexDimensionError,
    InvalidVectorError,
    VectorIndex,
    index_exists,
    load_index,
)


class RetrieverError(Exception):
    """Base class for all concrete-retriever errors (AI_ARCHITECTURE.md §16)."""


class EmptyQueryError(RetrieverError):
    """The query is blank or whitespace-only."""


class InvalidQueryError(RetrieverError):
    """The query is not a string."""


class EmbeddingProviderUnavailableError(RetrieverError):
    """No embedding provider is injected into the retriever (§15.1)."""


class QueryEmbeddingError(RetrieverError):
    """The injected embedding provider failed while embedding the query."""


class InvalidQueryVectorError(RetrieverError):
    """The query vector is empty, non-finite, or not cosine-normalizable."""


class DimensionMismatchError(RetrieverError):
    """The provider/index dimensions or query vector dimension disagree."""


class ModelParityError(RetrieverError):
    """The query embedding model differs from the index's model (§15.1/§15.2)."""


class IndexUnavailableError(RetrieverError):
    """No vector index is injected or no persisted index is configured (§15.2)."""


class SearchError(RetrieverError):
    """The FAISS search failed or returned invalid positions/scores."""


class RetrievedChunkError(RetrieverError):
    """A metadata mapping could not be converted to ``RetrievedChunk`` (§19.1)."""


class FaissRetriever:
    """Concrete cosine-similarity retriever over the FAISS vector index (§16).

    All collaborators are injected so the retriever is fully testable and
    offline: a fake deterministic ``EmbeddingProvider``, an in-memory
    ``VectorIndex`` built from synthetic vectors, and (optionally) the
    DB-owned "current version" state as a plain mapping. No client of any kind
    is constructed here — no Gemini/OpenAI/Groq, no network, no database.
    """

    def __init__(
        self,
        *,
        provider: EmbeddingProvider | None = None,
        vector_index: VectorIndex | None = None,
        top_k: int = 4,
        current_versions: Mapping[str, str] | None = None,
    ) -> None:
        """Configure the retriever (§16.5: ``top_k`` defaults to ``RAG_TOP_K``).

        ``current_versions`` maps a document's identity to its current active
        version (DATABASE_DESIGN.md §21.3). The identity is ``str(document_id)``
        when the chunk carries one, otherwise the document ``title``. A chunk
        whose document is listed at a different version is stale and skipped; a
        document absent from the map has no known currency constraint and is
        eligible. ``None`` disables the version filter entirely (offline tests /
        single-version corpora).
        """
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        self._provider = provider
        self._vector_index = vector_index
        self.top_k = top_k
        self._current_versions = (
            dict(current_versions) if current_versions is not None else None
        )
        self._embedding_service = (
            EmbeddingService(provider=provider) if provider is not None else None
        )

    def retrieve(
        self,
        *,
        query: str,
        categories: Sequence[str] = (),
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Return the best-matching eligible chunks for ``query`` (§16).

        Embedded via the injected provider, searched on the injected
        ``VectorIndex``, filtered by category scope + version currency, ranked
        deterministically by cosine score (ties by index position), and capped
        at ``top_k``. Each result is a ``RetrievedChunk`` whose ``score`` is the
        raw cosine similarity in [-1, 1] (§16.3).
        """
        if not isinstance(query, str):
            raise InvalidQueryError(f"query must be a string, got {type(query).__name__}")
        if not query.strip():
            raise EmptyQueryError("query must not be empty")
        resolved_top_k = self.top_k if top_k is None else top_k
        if resolved_top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        if self._provider is None:
            raise EmbeddingProviderUnavailableError(
                "no embedding provider is injected; pass provider=... (§15.1)"
            )
        if self._vector_index is None:
            raise IndexUnavailableError(
                "no vector index is injected; pass vector_index=... (§15.2)"
            )

        self._check_model_parity()
        if self._vector_index.count == 0:
            return []

        query_vector = self._embed_query(query)
        positions, scores = self._search(query_vector)

        hits = self._validated_hits(scores, positions)
        hits.sort(key=lambda hit: (-hit[0], hit[1]))

        requested = frozenset(
            (categories,) if isinstance(categories, str) else categories
        )
        results: list[RetrievedChunk] = []
        seen: set[str] = set()
        for score, position in hits:
            entry = self._vector_index.entries[position]
            if requested and entry.category not in requested:
                continue
            if not self._is_eligible(entry):
                continue
            if entry.chunk_id in seen:
                continue
            seen.add(entry.chunk_id)
            results.append(self._to_retrieved_chunk(entry, score))
            if len(results) == resolved_top_k:
                break
        return results

    def _check_model_parity(self) -> None:
        """Enforce §15.1 parity between the query provider and the index."""
        provider = self._provider
        index = self._vector_index
        assert provider is not None and index is not None
        if provider.model_name != index.model_name:
            raise ModelParityError(
                f"query embedding model {provider.model_name!r} does not match the "
                f"index model {index.model_name!r} (§15.1 model parity)"
            )
        if provider.dimension != index.dimension:
            raise DimensionMismatchError(
                f"query embedding dimension {provider.dimension} does not match the "
                f"index dimension {index.dimension}"
            )

    def _embed_query(self, query: str) -> list[float]:
        """Embed the query through the injected task-2 service, mapping errors."""
        service = self._embedding_service
        assert service is not None
        try:
            return service.embed_query(query)
        except EmbeddingError as exc:
            if isinstance(exc, EmptyEmbeddingInputError):
                raise EmptyQueryError(str(exc)) from exc
            if isinstance(exc, EmptyVectorError | EmbeddingInvalidVectorError):
                raise InvalidQueryVectorError(str(exc)) from exc
            if isinstance(exc, EmbeddingDimensionMismatchError):
                raise DimensionMismatchError(str(exc)) from exc
            raise QueryEmbeddingError(str(exc)) from exc

    def _search(self, query_vector: list[float]) -> tuple[list[int], list[float]]:
        """Run the FAISS search, mapping index errors to retriever errors."""
        index = self._vector_index
        assert index is not None
        try:
            return index.search(vector=query_vector, k=index.count)
        except FaissIndexError as exc:
            if isinstance(exc, IndexDimensionError):
                raise DimensionMismatchError(str(exc)) from exc
            if isinstance(exc, InvalidVectorError):
                raise InvalidQueryVectorError(str(exc)) from exc
            if isinstance(exc, FaissUnavailableError):
                raise SearchError(str(exc)) from exc
            raise SearchError(str(exc)) from exc
        except ValueError as exc:
            raise SearchError(str(exc)) from exc

    def _validated_hits(
        self, scores: Sequence[float], positions: Sequence[int]
    ) -> list[tuple[float, int]]:
        """Reject non-finite scores and out-of-range/invalid positions."""
        count = self._vector_index.count if self._vector_index is not None else 0
        hits: list[tuple[float, int]] = []
        for score, position in zip(scores, positions, strict=True):
            if not math.isfinite(score):
                raise SearchError("search returned a non-finite similarity score")
            if position < 0 or position >= count:
                raise SearchError(
                    f"search returned invalid position {position} (index size {count})"
                )
            hits.append((float(score), int(position)))
        return hits

    def _is_eligible(self, entry: ChunkEmbedding) -> bool:
        """Version-currency eligibility when current-version state is supplied."""
        if self._current_versions is None:
            return True
        current = self._current_versions.get(self._document_key(entry))
        if current is None:
            return True
        return entry.version == current

    @staticmethod
    def _document_key(entry: ChunkEmbedding) -> str:
        return str(entry.document_id) if entry.document_id is not None else entry.title

    @staticmethod
    def _to_retrieved_chunk(entry: ChunkEmbedding, score: float) -> RetrievedChunk:
        """Map the persisted metadata to the retrieval contract (§19.1).

        ``snippet`` is the full chunk text (the same unit the index embeds) and
        ``score`` is the raw cosine similarity from the index (§16.3). The
        richer source metadata (version/heading/source_path/chunk_index) stays
        on the index entry for the ContextBuilder and citation assembler.
        """
        try:
            return RetrievedChunk(
                chunk_id=entry.chunk_id,
                document_id=entry.document_id,
                title=entry.title,
                category=entry.category,
                snippet=entry.chunk_text,
                score=score,
            )
        except Exception as exc:
            raise RetrievedChunkError(
                f"cannot map chunk '{entry.chunk_id}' to RetrievedChunk: {exc}"
            ) from exc


def create_faiss_retriever(
    settings: Settings,
    *,
    provider: EmbeddingProvider | None = None,
    vector_index: VectorIndex | None = None,
    top_k: int | None = None,
) -> FaissRetriever:
    """Build the configured retriever (§15.1/§15.2/§16.5 config-driven glue).

    The provider is the configured Sentence Transformers provider and the index
    is loaded from ``Settings.vector_store_path`` unless an in-memory index or
    provider is injected. A missing persisted index raises ``IndexUnavailableError``;
    a present-but-corrupt/incompatible index surfaces the precise
    ``FaissIndexError`` from ``load_index`` instead of silently rebuilding.
    """
    resolved_provider = provider if provider is not None else create_embedding_provider(settings)
    resolved_index = vector_index
    if resolved_index is None:
        index_path = Path(settings.vector_store_path)
        if not index_exists(path=index_path):
            raise IndexUnavailableError(
                "no persisted vector index at "
                f"'{settings.vector_store_path}'; ingest and index the knowledge "
                "base (Phase 9 task 7 re-index job) before retrieving"
            )
        resolved_index = load_index(path=index_path)
    return FaissRetriever(
        provider=resolved_provider,
        vector_index=resolved_index,
        top_k=settings.rag_top_k if top_k is None else top_k,
    )

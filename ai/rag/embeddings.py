"""Embedding generation for knowledge chunks and queries (AI_ARCHITECTURE.md §15).

§15.1 fixes the architecture: a Sentence Transformers encoder (bilingual-capable)
embeds both documents and queries, so query and corpus vectors live in the same
space ("model parity" is guaranteed by using one provider instance for both
paths). Documents are embedded in batches; queries are embedded individually at
request time. Vectors have a fixed dimension per model, and embedding runs
locally inside the AI service — there is no external API call per chunk.

The concrete Sentence Transformer model is config-driven (``EMBEDDING_MODEL``)
and loaded lazily so tests never download or load model weights: production code
talks to an ``EmbeddingProvider`` protocol and tests inject a deterministic fake
provider. Real model loading is isolated in
``SentenceTransformerEmbeddingProvider`` and only triggers on first embed
request.

§15.2 / §21.2: the embedding output stays associated with its source chunk —
``ChunkEmbedding`` carries the chunk id, document id, source path, category,
version and chunk index alongside the vector, which is what the FAISS index
(Phase 9, task 3) will later key on. The chunk text itself is the embedding
input; metadata is stored beside the vector, never mixed into the embedding
text (§21.2). §15.4 (lifecycle) drives re-embedding decisions externally; this
module only generates and validates vectors.
"""

from __future__ import annotations

import importlib.util
import math
import uuid
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from ai.core.config import Settings
from ai.rag.ingestion import DocumentChunk, normalize_text


class EmbeddingError(Exception):
    """Base class for all embedding-generation errors."""


class EmbeddingProviderError(EmbeddingError):
    """The embedding provider is unavailable, unconfigured, or failed."""


class EmptyEmbeddingInputError(EmbeddingError):
    """No chunks (or a blank query) were provided to embed."""


class EmptyVectorError(EmbeddingError):
    """The provider returned an empty vector for a non-empty input."""


class DimensionMismatchError(EmbeddingError):
    """A returned vector does not match the provider's fixed dimension."""


class InvalidVectorError(EmbeddingError):
    """A returned vector contains non-finite values (NaN/inf)."""


class CountMismatchError(EmbeddingError):
    """The provider returned a different number of vectors than inputs."""


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Contract for an embedding model provider (AI_ARCHITECTURE.md §15.1).

    The provider owns a single model so that queries and documents are always
    embedded in the same space. ``dimension`` is the fixed vector length the
    model produces; the service rejects any vector that deviates from it.
    """

    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed(self, *, text: str) -> list[float]:
        """Embed a single text (query path)."""
        ...

    def embed_batch(self, *, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple texts in order (document path, §15.1 batching)."""
        ...


class ChunkEmbedding(BaseModel):
    """One chunk's embedding plus its source metadata (§15.2, §21.2).

    The vector is the fixed-dimension embedding of ``chunk_text``. The model
    name is recorded alongside the vector so the index can be reproduced or
    invalidated when the model changes (§15.2 model-parity bookkeeping).
    ``chunk_text`` is the original chunk text — required to reconstruct
    ``RetrievedChunk.snippet`` (§19.1) from a persisted FAISS metadata mapping.
    """

    chunk_id: str = Field(min_length=1, max_length=64)
    document_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1)
    version: str = Field(min_length=1, max_length=30)
    source_path: str = ""
    chunk_index: int = Field(ge=0)
    heading: str | None = None
    model_name: str = Field(min_length=1)
    chunk_text: str = Field(min_length=1)
    vector: list[float] = Field(min_length=1)

    @property
    def dimension(self) -> int:
        """The vector's length — must equal the provider's fixed dimension."""
        return len(self.vector)


def prepare_embedding_input(chunk: DocumentChunk) -> str:
    """The deterministic embedding input for a chunk (§15.4, §21.2).

    The chunk text is the embedding input; metadata (title, category, source)
    is carried beside the vector, not concatenated into it, matching the
    architecture. Line endings are normalized so identical content always
    produces identical input (and therefore identical vectors for a fixed
    model), independent of platform.
    """
    return normalize_text(chunk.chunk_text)


class SentenceTransformerEmbeddingProvider:
    """Architecture-approved Sentence Transformers provider (§15.1).

    The model is loaded lazily on the first embed request, so constructing the
    provider never downloads weights and tests never need a real model. When
    the ``sentence_transformers`` package is unavailable, every embed request
    fails with a clear ``EmbeddingProviderError`` instead of an import error.
    """

    def __init__(self, *, model_name: str) -> None:
        if not model_name or not model_name.strip():
            raise EmbeddingProviderError("an embedding model name is required")
        self._model_name = model_name
        self._model: Any | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        """The fixed vector dimension of the configured model (loads lazily)."""
        return int(self._load().get_sentence_embedding_dimension())

    def embed(self, *, text: str) -> list[float]:
        return [float(value) for value in self._load().encode(text)]

    def embed_batch(self, *, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._load().encode(list(texts))
        return [[float(value) for value in row] for row in vectors]

    def _load(self) -> Any:
        """Load the Sentence Transformer model on first use (§15.4 lazy load)."""
        if self._model is None:
            if importlib.util.find_spec("sentence_transformers") is None:
                raise EmbeddingProviderError(
                    "sentence-transformers is not installed; install the AI "
                    "service requirements to embed with the configured model "
                    f"'{self._model_name}' (AI_ARCHITECTURE.md §15.1)"
                )
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - import environment
                raise EmbeddingProviderError(
                    "failed to import sentence_transformers: "
                    f"{exc}"
                ) from exc
            try:
                self._model = SentenceTransformer(self._model_name)
            except Exception as exc:
                raise EmbeddingProviderError(
                    "failed to load Sentence Transformer model "
                    f"'{self._model_name}': {exc}"
                ) from exc
        return self._model


class EmbeddingService:
    """Orchestrates chunk/query embedding and validates every vector (§15.1).

    ``embed_chunks`` feeds batches of chunk texts to the provider (batched per
    §15.1 for documents) and rebuilds the chunk-to-vector association. It is
    deliberately pure: it performs no retrieval, ranking, or persistence — the
    FAISS index (task 3) consumes the returned ``ChunkEmbedding`` records.
    """

    def __init__(self, *, provider: EmbeddingProvider, batch_size: int = 32) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        self.provider = provider
        self.batch_size = batch_size

    def embed_chunks(self, chunks: Sequence[DocumentChunk]) -> list[ChunkEmbedding]:
        """Embed document chunks in batches, preserving input order (§15.1)."""
        if not chunks:
            raise EmptyEmbeddingInputError("no chunks to embed")
        for chunk in chunks:
            if not isinstance(chunk, DocumentChunk):
                raise EmbeddingError(
                    f"expected DocumentChunk, got {type(chunk).__name__}"
                )

        texts = [prepare_embedding_input(chunk) for chunk in chunks]
        vectors = self._embed_in_batches(texts)
        if len(vectors) != len(chunks):
            raise CountMismatchError(
                f"expected {len(chunks)} vectors, got {len(vectors)}"
            )

        dimension = self.provider.dimension
        results: list[ChunkEmbedding] = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            self._validate_vector(vector, dimension, chunk.chunk_id)
            results.append(
                ChunkEmbedding(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    category=chunk.category,
                    version=chunk.version,
                    source_path=chunk.source_path,
                    chunk_index=chunk.chunk_index,
                    heading=chunk.heading,
                    model_name=self.provider.model_name,
                    chunk_text=chunk.chunk_text,
                    vector=vector,
                )
            )
        return results

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query with the same model used for documents (§15.1)."""
        if not query.strip():
            raise EmptyEmbeddingInputError("query must not be empty")
        try:
            vector = self.provider.embed(text=query)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(f"embedding provider failed: {exc}") from exc
        self._validate_vector(vector, self.provider.dimension, "<query>")
        return vector

    def _embed_in_batches(self, texts: list[str]) -> list[list[float]]:
        """Embed ``texts`` in fixed-size batches, checking count per batch."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            try:
                embedded = self.provider.embed_batch(texts=batch)
            except EmbeddingError:
                raise
            except Exception as exc:
                raise EmbeddingProviderError(
                    f"embedding provider failed: {exc}"
                ) from exc
            if len(embedded) != len(batch):
                raise CountMismatchError(
                    f"expected {len(batch)} vectors for a batch, "
                    f"got {len(embedded)}"
                )
            vectors.extend(embedded)
        return vectors

    def _validate_vector(
        self, vector: list[float], dimension: int, label: str
    ) -> None:
        """Reject empty, mis-sized, or non-finite vectors deterministically."""
        if not vector:
            raise EmptyVectorError(f"provider returned an empty vector for {label}")
        if len(vector) != dimension:
            raise DimensionMismatchError(
                f"expected dimension {dimension}, got {len(vector)} for {label}"
            )
        if not all(math.isfinite(value) for value in vector):
            raise InvalidVectorError(
                f"vector for {label} contains non-finite values"
            )


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the configured Sentence Transformers provider (§15.1 config-driven).

    Fails fast (without loading a model) when ``EMBEDDING_MODEL`` is unset so
    misconfiguration surfaces at construction, not at first embed request.
    """
    model_name = settings.embedding_model
    if not model_name or not model_name.strip():
        raise EmbeddingProviderError(
            "EMBEDDING_MODEL is not configured; set it to a Sentence "
            "Transformers model id (AI_ARCHITECTURE.md §15.1)"
        )
    return SentenceTransformerEmbeddingProvider(model_name=model_name)

"""Embedding generation tests (Phase 9 RAG, task 2).

Sources: IMPLEMENTATION_PLAN.md §4 RAG task 2; AI_ARCHITECTURE.md §15.1
(Sentence Transformers bilingual-capable encoder, model parity, batched
document embedding, individual query embedding, fixed dimension, locality),
§15.2 (vector-to-chunk association, model name bookkeeping), §15.4 (lifecycle,
lazy load), §21.2 (chunk metadata stored beside the vector); DATABASE_DESIGN.md
§21.3; TESTING_STRATEGY.md §12.1.

All behavior is deterministic and offline: the production provider is never
given a real model, tests inject a ``FakeEmbeddingProvider``, and the real
provider's lazy-load path is exercised with a monkeypatched
``sentence_transformers`` module — no model weights are downloaded, no network
call is made, and no API-based embeddings are used.
"""

from __future__ import annotations

import hashlib
import math
import sys
import types
import uuid
from typing import Any

import pytest

from ai.core.config import TestingSettings
from ai.rag import embeddings
from ai.rag.embeddings import (
    ChunkEmbedding,
    CountMismatchError,
    DimensionMismatchError,
    EmbeddingError,
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingService,
    EmptyEmbeddingInputError,
    EmptyVectorError,
    InvalidVectorError,
    SentenceTransformerEmbeddingProvider,
    create_embedding_provider,
    prepare_embedding_input,
)
from ai.rag.ingestion import DocumentChunk

SAMPLE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def make_chunk(
    chunk_id: str = "c1",
    *,
    text: str = "Applicants need 60% in intermediate to be eligible.",
    document_id: uuid.UUID | None = None,
    chunk_index: int = 0,
    heading: str | None = None,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        title="Admission Policy",
        category="admission",
        version="1",
        source_path="knowledge/admission/admission.md",
        chunk_index=chunk_index,
        heading=heading,
        chunk_text=text,
        token_count=len(text.split()),
        character_count=len(text),
        checksum_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


class FakeEmbeddingProvider:
    """Deterministic, offline stand-in for a Sentence Transformer (§15.1).

    ``vectors`` can override per-text output so tests can inject empty, wrong
    length, or non-finite vectors; ``embed_error``/``batch_error`` simulate a
    failing provider. Vectors are derived from a stable SHA-256 digest so
    identical input always yields identical vectors.
    """

    def __init__(
        self,
        *,
        model_name: str = "fake/sentence-model",
        dimension: int = 4,
        vectors: dict[str, list[float]] | None = None,
        embed_error: BaseException | None = None,
        batch_error: BaseException | None = None,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.vectors = vectors
        self.embed_error = embed_error
        self.batch_error = batch_error
        self.embed_calls: list[str] = []
        self.batch_calls: list[list[str]] = []

    def _vector(self, text: str) -> list[float]:
        if self.vectors is not None:
            return self.vectors[text]
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [float(digest[i % len(digest)]) / 255.0 for i in range(self.dimension)]

    def embed(self, *, text: str) -> list[float]:
        self.embed_calls.append(text)
        if self.embed_error is not None:
            raise self.embed_error
        return self._vector(text)

    def embed_batch(self, *, texts: list[str]) -> list[list[float]]:
        self.batch_calls.append(list(texts))
        if self.batch_error is not None:
            raise self.batch_error
        return [self._vector(text) for text in texts]


class _FakeSentenceTransformer:
    instances = 0

    def __init__(self, name: str) -> None:
        self.name = name
        type(self).instances += 1

    def get_sentence_embedding_dimension(self) -> int:
        return 2

    def encode(self, inputs: Any) -> Any:
        if isinstance(inputs, str):
            return [0.5, 0.25]
        return [[0.5, 0.25] for _ in inputs]


def _install_fake_sentence_transformers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route the lazy import in ``_load`` to an offline fake module."""
    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = _FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setattr(
        embeddings.importlib.util, "find_spec", lambda name: object()
    )


# --- 1. Embedding provider contract ---------------------------------------


def test_fake_provider_satisfies_embedding_provider_protocol() -> None:
    assert isinstance(FakeEmbeddingProvider(), EmbeddingProvider)


def test_nonconforming_object_is_not_an_embedding_provider() -> None:
    class NotAProvider:
        pass

    assert not isinstance(NotAProvider(), EmbeddingProvider)


# --- 2. Single-chunk embedding ---------------------------------------------


def test_embed_chunks_embeds_one_chunk() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    service = EmbeddingService(provider=provider)
    chunk = make_chunk()

    records = service.embed_chunks([chunk])

    assert len(records) == 1
    assert len(records[0].vector) == 4
    assert provider.batch_calls == [["Applicants need 60% in intermediate to be eligible."]]


# --- 3. Batch embedding -----------------------------------------------------


def test_embed_chunks_batches_documents_in_order() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    service = EmbeddingService(provider=provider, batch_size=2)
    chunks = [make_chunk(f"c{i}", text=f"Chunk text {i}.") for i in range(5)]

    records = service.embed_chunks(chunks)

    assert len(records) == 5
    assert provider.batch_calls == [
        ["Chunk text 0.", "Chunk text 1."],
        ["Chunk text 2.", "Chunk text 3."],
        ["Chunk text 4."],
    ]


# --- 4. Input ordering is preserved ----------------------------------------


def test_embed_chunks_preserves_input_order() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    service = EmbeddingService(provider=provider)
    chunks = [make_chunk(f"c{i}", text=f"Chunk text {i}.") for i in range(3)]

    records = service.embed_chunks(chunks)

    for record, chunk in zip(records, chunks, strict=True):
        assert record.vector == provider._vector(chunk.chunk_text)


# --- 5. Chunk-id association ------------------------------------------------


def test_embed_chunks_associates_vector_with_chunk_id() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    service = EmbeddingService(provider=provider)
    chunks = [make_chunk(f"c{i}", text=f"Chunk text {i}.") for i in range(3)]

    records = service.embed_chunks(chunks)

    assert [record.chunk_id for record in records] == ["c0", "c1", "c2"]


# --- 6. Query and document use the same model ------------------------------


def test_query_and_documents_share_the_provider_model() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    service = EmbeddingService(provider=provider)
    query = "When does the application window open?"

    vector = service.embed_query(query)

    assert vector == provider._vector(query)
    assert provider.embed_calls == [query]
    chunk_record = service.embed_chunks([make_chunk(text=query)])
    assert chunk_record[0].vector == vector


# --- 7. Vector dimension validation -----------------------------------------


def test_dimension_mismatch_is_rejected() -> None:
    provider = FakeEmbeddingProvider(
        dimension=3,
        vectors={"x": [0.1, 0.2, 0.3, 0.4]},
    )
    service = EmbeddingService(provider=provider)
    chunk = make_chunk(text="x")

    with pytest.raises(DimensionMismatchError, match="expected dimension 3"):
        service.embed_chunks([chunk])


def test_query_dimension_mismatch_is_rejected() -> None:
    provider = FakeEmbeddingProvider(
        dimension=3,
        vectors={"x": [0.1, 0.2, 0.3, 0.4]},
    )
    service = EmbeddingService(provider=provider)

    with pytest.raises(DimensionMismatchError, match="expected dimension 3"):
        service.embed_query("x")


# --- 8. Empty input handling ------------------------------------------------


def test_empty_chunk_list_is_rejected() -> None:
    service = EmbeddingService(provider=FakeEmbeddingProvider())

    with pytest.raises(EmptyEmbeddingInputError, match="no chunks"):
        service.embed_chunks([])


@pytest.mark.parametrize("query", ["", "   "])
def test_blank_query_is_rejected(query: str) -> None:
    service = EmbeddingService(provider=FakeEmbeddingProvider())

    with pytest.raises(EmptyEmbeddingInputError, match="query"):
        service.embed_query(query)


def test_invalid_chunk_object_is_rejected() -> None:
    service = EmbeddingService(provider=FakeEmbeddingProvider())

    with pytest.raises(EmbeddingError, match="DocumentChunk"):
        service.embed_chunks(["not-a-chunk"])  # type: ignore[list-item]


# --- 9. Empty vector handling -----------------------------------------------


def test_empty_vector_is_rejected() -> None:
    provider = FakeEmbeddingProvider(vectors={"x": []})
    service = EmbeddingService(provider=provider)

    with pytest.raises(EmptyVectorError, match="empty vector"):
        service.embed_chunks([make_chunk(text="x")])


# --- 10. Wrong vector count handling ---------------------------------------


def test_wrong_vector_count_is_rejected() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    provider.batch_error = CountMismatchError(
        "expected 2 vectors for a batch, got 1"
    )
    service = EmbeddingService(provider=provider)
    chunks = [make_chunk("c0", text="a."), make_chunk("c1", text="b.")]

    with pytest.raises(CountMismatchError, match="got 1"):
        service.embed_chunks(chunks)


def test_shorter_provider_batch_result_is_rejected() -> None:
    class ShortProvider(FakeEmbeddingProvider):
        def embed_batch(self, *, texts: list[str]) -> list[list[float]]:
            return [self._vector(texts[0])]

    service = EmbeddingService(provider=ShortProvider(dimension=4))
    chunks = [make_chunk("c0", text="a."), make_chunk("c1", text="b.")]

    with pytest.raises(CountMismatchError):
        service.embed_chunks(chunks)


# --- 11. Non-finite vector handling ----------------------------------------


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_non_finite_vector_is_rejected(bad_value: float) -> None:
    provider = FakeEmbeddingProvider(
        dimension=4,
        vectors={"x": [0.1, bad_value, 0.3, 0.4]},
    )
    service = EmbeddingService(provider=provider)

    with pytest.raises(InvalidVectorError, match="non-finite"):
        service.embed_chunks([make_chunk(text="x")])


# --- 12. Provider failure handling -----------------------------------------


def test_typed_provider_error_propagates_unchanged() -> None:
    provider = FakeEmbeddingProvider(
        batch_error=EmbeddingProviderError("model unavailable")
    )
    service = EmbeddingService(provider=provider)

    with pytest.raises(EmbeddingProviderError, match="model unavailable"):
        service.embed_chunks([make_chunk()])


def test_raw_provider_exception_is_wrapped() -> None:
    provider = FakeEmbeddingProvider(batch_error=RuntimeError("boom"))
    service = EmbeddingService(provider=provider)

    with pytest.raises(EmbeddingProviderError, match="boom"):
        service.embed_chunks([make_chunk()])


def test_raw_query_provider_exception_is_wrapped() -> None:
    provider = FakeEmbeddingProvider(embed_error=RuntimeError("boom"))
    service = EmbeddingService(provider=provider)

    with pytest.raises(EmbeddingProviderError, match="boom"):
        service.embed_query("a query")


# --- 13. Configured model/dimension behavior --------------------------------


def test_factory_requires_configured_model() -> None:
    with pytest.raises(EmbeddingProviderError, match="EMBEDDING_MODEL"):
        create_embedding_provider(TestingSettings())


def test_factory_builds_provider_with_configured_model_name() -> None:
    settings = TestingSettings(embedding_model=SAMPLE_MODEL)

    provider = create_embedding_provider(settings)

    assert isinstance(provider, SentenceTransformerEmbeddingProvider)
    assert provider.model_name == SAMPLE_MODEL


def test_real_provider_requires_a_model_name() -> None:
    with pytest.raises(EmbeddingProviderError, match="model name"):
        SentenceTransformerEmbeddingProvider(model_name="")


def test_embedding_service_uses_configured_batch_size() -> None:
    provider = FakeEmbeddingProvider()
    service = EmbeddingService(provider=provider, batch_size=1)
    chunks = [make_chunk(f"c{i}", text=f"Chunk {i}.") for i in range(3)]

    service.embed_chunks(chunks)

    assert provider.batch_calls == [["Chunk 0."], ["Chunk 1."], ["Chunk 2."]]


def test_embedding_service_rejects_non_positive_batch_size() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        EmbeddingService(provider=FakeEmbeddingProvider(), batch_size=0)


# --- 14. Fake provider injection -------------------------------------------


def test_service_injects_fake_provider_and_records_inputs() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    service = EmbeddingService(provider=provider, batch_size=2)
    chunks = [make_chunk(f"c{i}", text=f"Chunk {i}.") for i in range(3)]

    service.embed_chunks(chunks)

    assert provider.batch_calls == [["Chunk 0.", "Chunk 1."], ["Chunk 2."]]


# --- 15. Lazy loading / no network -----------------------------------------


def test_real_provider_does_not_load_at_construction(monkeypatch) -> None:
    _install_fake_sentence_transformers(monkeypatch)
    _FakeSentenceTransformer.instances = 0

    provider = SentenceTransformerEmbeddingProvider(model_name=SAMPLE_MODEL)

    assert _FakeSentenceTransformer.instances == 0
    assert provider.model_name == SAMPLE_MODEL


def test_real_provider_loads_lazily_and_embeds(monkeypatch) -> None:
    _install_fake_sentence_transformers(monkeypatch)
    _FakeSentenceTransformer.instances = 0
    provider = SentenceTransformerEmbeddingProvider(model_name=SAMPLE_MODEL)

    assert provider.dimension == 2
    assert _FakeSentenceTransformer.instances == 1
    assert provider.embed(text="hello world") == [0.5, 0.25]
    assert provider.embed_batch(texts=["a", "b"]) == [[0.5, 0.25], [0.5, 0.25]]
    assert _FakeSentenceTransformer.instances == 1


def test_real_provider_without_package_raises_typed_error(monkeypatch) -> None:
    monkeypatch.setattr(embeddings.importlib.util, "find_spec", lambda name: None)
    provider = SentenceTransformerEmbeddingProvider(model_name=SAMPLE_MODEL)

    with pytest.raises(EmbeddingProviderError, match="sentence-transformers"):
        provider.embed(text="hello")


# --- Embedding input preparation -------------------------------------------


def test_prepare_embedding_input_is_chunk_text_only() -> None:
    chunk = make_chunk(
        text="Applicants need 60% in intermediate.",
        heading="Eligibility",
    )

    assert prepare_embedding_input(chunk) == "Applicants need 60% in intermediate."
    assert "Eligibility" not in prepare_embedding_input(chunk)


def test_prepare_embedding_input_normalizes_line_endings() -> None:
    chunk = make_chunk(text="Line one.\r\nLine two.")

    assert prepare_embedding_input(chunk) == "Line one.\nLine two."


# --- Metadata association ---------------------------------------------------


def test_chunk_embedding_preserves_source_metadata() -> None:
    doc_id = uuid.uuid4()
    provider = FakeEmbeddingProvider()
    service = EmbeddingService(provider=provider)
    chunk = make_chunk(
        "c1",
        text="Some admission text.",
        document_id=doc_id,
        chunk_index=3,
        heading="Eligibility",
    )

    record = service.embed_chunks([chunk])[0]

    assert record.document_id == doc_id
    assert record.title == "Admission Policy"
    assert record.category == "admission"
    assert record.version == "1"
    assert record.source_path == "knowledge/admission/admission.md"
    assert record.chunk_index == 3
    assert record.heading == "Eligibility"
    assert record.chunk_text == chunk.chunk_text
    assert record.model_name == provider.model_name


def test_chunk_embedding_dimension_property_matches_vector() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    service = EmbeddingService(provider=provider)

    record = service.embed_chunks([make_chunk()])[0]

    assert record.dimension == 4
    assert len(record.vector) == record.dimension


def test_chunk_embedding_is_a_pydantic_model() -> None:
    record = ChunkEmbedding(
        chunk_id="c1",
        title="Admission Policy",
        category="admission",
        version="1",
        source_path="knowledge/admission/admission.md",
        chunk_index=0,
        model_name="fake/sentence-model",
        chunk_text="Some admission text.",
        vector=[0.1, 0.2, 0.3, 0.4],
    )

    assert record.dimension == 4
    assert record.document_id is None
    assert record.heading is None


# --- Determinism ------------------------------------------------------------


def test_embed_chunks_is_deterministic_for_fixed_model() -> None:
    chunks = [make_chunk(f"c{i}", text=f"Chunk {i}.") for i in range(3)]
    first = EmbeddingService(provider=FakeEmbeddingProvider(dimension=4)).embed_chunks(
        chunks
    )
    second = EmbeddingService(provider=FakeEmbeddingProvider(dimension=4)).embed_chunks(
        chunks
    )

    assert [record.vector for record in first] == [
        record.vector for record in second
    ]


def test_embed_query_is_deterministic_for_fixed_model() -> None:
    service = EmbeddingService(provider=FakeEmbeddingProvider(dimension=4))

    assert service.embed_query("When does the window open?") == service.embed_query(
        "When does the window open?"
    )


# --- Error hierarchy --------------------------------------------------------


def test_error_hierarchy_is_typed() -> None:
    assert issubclass(EmbeddingProviderError, EmbeddingError)
    assert issubclass(EmptyEmbeddingInputError, EmbeddingError)
    assert issubclass(EmptyVectorError, EmbeddingError)
    assert issubclass(DimensionMismatchError, EmbeddingError)
    assert issubclass(InvalidVectorError, EmbeddingError)
    assert issubclass(CountMismatchError, EmbeddingError)

"""Knowledge re-indexing background job tests (IMPLEMENTATION_PLAN.md §4 RAG task 7).

Offline by construction: temporary knowledge roots, a deterministic fake
embedding provider, and on-disk FAISS indexes in ``tmp_path`` — no model
weights, no network, no API keys, no database (TESTING_STRATEGY.md §13.5,
§23.2). Covers the task 7 requirements: the full ingest → embed → index job,
checksum/version change detection + idempotent re-runs, carry-forward of
unchanged chunks, atomic swap + manifest persistence, golden-set verification
before swap, corrupt-index recovery, and the async background-job entry point.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from ai.core.config import Settings
from ai.rag.embeddings import EmbeddingProviderError
from ai.rag.faiss_index import VectorIndex, index_exists, load_index
from ai.rag.ingestion import KnowledgeIngestor
from ai.rag.reindexer import (
    KnowledgeReindexer,
    ReindexEmbeddingError,
    ReindexEmptyError,
    ReindexError,
    ReindexVerificationError,
)

MODEL_NAME = "fake/sentence-model"

ADMISSION_BODY = (
    "Applicants must have secured at least 60 percent marks in the intermediate "
    "examination to be considered for admission. Admission is merit-based and "
    "seats are awarded in order of merit."
)
ADMISSION_BODY_MODIFIED = (
    "Applicants must have secured at least 65 percent marks in the intermediate "
    "examination to be considered for admission. Admission is merit-based and "
    "seats are awarded in order of merit."
)
FAQ_BODY = (
    "The registrar's office is open from 9:00 am to 5:00 pm from Monday to Friday."
)


class FakeEmbeddingProvider:
    """Deterministic, offline stand-in for a Sentence Transformer (§15.1)."""

    def __init__(
        self,
        *,
        model_name: str = MODEL_NAME,
        dimension: int = 4,
        embed_error: BaseException | None = None,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.embed_error = embed_error
        self.embed_batch_calls: list[list[str]] = []

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [float(digest[i % len(digest)]) / 255.0 for i in range(self.dimension)]

    def embed(self, *, text: str) -> list[float]:
        if self.embed_error is not None:
            raise self.embed_error
        return self._vector(text)

    def embed_batch(self, *, texts: Sequence[str]) -> list[list[float]]:
        if self.embed_error is not None:
            raise self.embed_error
        self.embed_batch_calls.append(list(texts))
        return [self._vector(text) for text in texts]


def write_document(
    root: Path,
    source: str,
    category: str,
    body: str,
    *,
    title: str | None = None,
    version: str = "1",
) -> Path:
    """Write a markdown knowledge document with a front-matter header."""
    path = root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"---\ntitle: {title or path.stem}\n"
        f"category: {category}\nversion: {version}\n---\n\n"
    )
    path.write_text(header + body, encoding="utf-8")
    return path


def make_settings(root: Path) -> Settings:
    return Settings(
        knowledge_root=str(root),
        vector_store_path=str(root / "vectorstore"),
        embedding_model=MODEL_NAME,
        _env_file=None,
    )


def make_ingestor(root: Path) -> KnowledgeIngestor:
    return KnowledgeIngestor(root)


def index_pair_bytes(root: Path) -> tuple[bytes, bytes]:
    store = root / "vectorstore"
    return (store / "index.faiss").read_bytes(), (store / "metadata.json").read_bytes()


def manifest(root: Path) -> dict[str, object]:
    payload = json.loads((root / "vectorstore" / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def build_corpus(root: Path) -> None:
    write_document(
        root,
        "admission/admission-policy.md",
        "admission",
        ADMISSION_BODY,
        title="Admission Policy",
    )
    write_document(root, "faq/faq.md", "faq", FAQ_BODY, title="University FAQ")


# --- 1. First run -----------------------------------------------------------


def test_first_run_builds_index_and_reports_counts(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    provider = FakeEmbeddingProvider()
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=provider
    )

    report = reindexer.run()

    assert report.status == "completed"
    assert report.documents_found == 2
    assert report.documents_changed == 2
    assert report.documents_unchanged == 0
    assert report.chunks_embedded == 2
    assert report.chunks_carried_forward == 0
    assert report.index_count == 2
    assert report.index_path == settings.vector_store_path
    assert report.warnings == []

    assert index_exists(path=settings.vector_store_path)
    loaded = load_index(path=settings.vector_store_path)
    assert loaded.count == 2
    assert loaded.model_name == MODEL_NAME
    assert loaded.dimension == 4

    payload = manifest(tmp_path)
    assert payload["version"] == 1
    documents = payload["documents"]
    assert isinstance(documents, dict)
    assert set(documents) == {
        "admission/admission-policy.md",
        "faq/faq.md",
    }


# --- 2. Idempotency ---------------------------------------------------------


def test_repeat_run_is_idempotent_and_unchanged(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    provider = FakeEmbeddingProvider()
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=provider
    )
    reindexer.run()

    before = index_pair_bytes(tmp_path)
    embed_calls_before = len(provider.embed_batch_calls)

    report = reindexer.run()

    assert report.status == "unchanged"
    assert report.documents_found == 2
    assert report.documents_changed == 0
    assert report.documents_unchanged == 2
    assert report.chunks_embedded == 0
    assert report.chunks_carried_forward == 2
    assert report.index_count == 2
    assert index_pair_bytes(tmp_path) == before
    assert len(provider.embed_batch_calls) == embed_calls_before


# --- 3. Change detection ----------------------------------------------------


def test_changed_document_triggers_partial_reembed(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    provider = FakeEmbeddingProvider()
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=provider
    )
    first = reindexer.run()
    assert first.index_count == 2

    write_document(
        tmp_path,
        "admission/admission-policy.md",
        "admission",
        ADMISSION_BODY_MODIFIED,
        title="Admission Policy",
    )

    second = reindexer.run()

    assert second.status == "completed"
    assert second.documents_found == 2
    assert second.documents_changed == 1
    assert second.documents_unchanged == 1
    assert second.chunks_embedded == 1
    assert second.chunks_carried_forward == 1
    assert second.index_count == 2

    loaded = load_index(path=settings.vector_store_path)
    by_source: dict[str, str] = {
        entry.source_path: entry.chunk_text for entry in loaded.entries
    }
    assert by_source["admission/admission-policy.md"] == ADMISSION_BODY_MODIFIED
    assert by_source["faq/faq.md"] == FAQ_BODY

    third = reindexer.run()
    assert third.status == "unchanged"
    assert third.chunks_embedded == 0


def test_added_document_grows_the_index(tmp_path: Path) -> None:
    write_document(
        tmp_path, "admission/admission-policy.md", "admission", ADMISSION_BODY
    )
    settings = make_settings(tmp_path)
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=FakeEmbeddingProvider()
    )
    first = reindexer.run()
    assert first.index_count == 1

    write_document(tmp_path, "faq/faq.md", "faq", FAQ_BODY)
    second = reindexer.run()

    assert second.status == "completed"
    assert second.documents_found == 2
    assert second.documents_changed == 1
    assert second.documents_unchanged == 1
    assert second.chunks_embedded == 1
    assert second.chunks_carried_forward == 1
    assert second.index_count == 2


def test_removed_document_shrinks_the_index(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=FakeEmbeddingProvider()
    )
    assert reindexer.run().index_count == 2

    (tmp_path / "faq" / "faq.md").unlink()
    second = reindexer.run()

    assert second.status == "completed"
    assert second.documents_found == 1
    assert second.documents_unchanged == 1
    assert second.index_count == 1
    loaded = load_index(path=settings.vector_store_path)
    assert {entry.source_path for entry in loaded.entries} == {
        "admission/admission-policy.md"
    }


# --- 4. Safety: no clobbering -----------------------------------------------


def test_empty_knowledge_root_raises_and_keeps_index(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=FakeEmbeddingProvider()
    )
    reindexer.run()
    before = index_pair_bytes(tmp_path)

    for document in tmp_path.rglob("*.md"):
        document.unlink()

    with pytest.raises(ReindexEmptyError):
        reindexer.run()

    assert index_pair_bytes(tmp_path) == before
    assert load_index(path=settings.vector_store_path).count == 2


def test_embedding_failure_raises_and_keeps_index(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    reindexer = KnowledgeReindexer(
        settings=settings,
        ingestor=make_ingestor(tmp_path),
        provider=FakeEmbeddingProvider(embed_error=EmbeddingProviderError("boom")),
    )
    with pytest.raises(ReindexEmbeddingError):
        reindexer.run()
    assert not index_exists(path=settings.vector_store_path)


def test_corrupt_index_is_recovered_by_full_rebuild(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=FakeEmbeddingProvider()
    )
    assert reindexer.run().status == "completed"

    index_file = tmp_path / "vectorstore" / "index.faiss"
    index_file.write_bytes(b"corrupt-not-a-faiss-index")

    report = reindexer.run()

    assert report.status == "completed"
    assert report.documents_changed == 2
    assert any("unreadable" in warning for warning in report.warnings)
    assert load_index(path=settings.vector_store_path).count == 2


def test_missing_manifest_reembeds_everything(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=FakeEmbeddingProvider()
    )
    reindexer.run()

    (tmp_path / "vectorstore" / "manifest.json").unlink()
    report = reindexer.run()

    assert report.status == "completed"
    assert report.documents_changed == 2
    assert any("manifest" in warning for warning in report.warnings)
    assert load_index(path=settings.vector_store_path).count == 2


# --- 5. Golden-set verification before swap (TESTING_STRATEGY.md §13.5) -----


def test_verify_before_swap_passes_and_swaps(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    seen: list[VectorIndex] = []

    def verifier(candidate: VectorIndex) -> bool:
        seen.append(candidate)
        return True

    reindexer = KnowledgeReindexer(
        settings=settings,
        ingestor=make_ingestor(tmp_path),
        provider=FakeEmbeddingProvider(),
        verify_before_swap=verifier,
    )
    report = reindexer.run()

    assert report.status == "completed"
    assert len(seen) == 1
    assert seen[0].count == 2
    assert index_exists(path=settings.vector_store_path)


def test_failed_verification_aborts_the_swap(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=FakeEmbeddingProvider()
    )
    reindexer.run()
    before = index_pair_bytes(tmp_path)

    write_document(
        tmp_path,
        "admission/admission-policy.md",
        "admission",
        ADMISSION_BODY_MODIFIED,
        title="Admission Policy",
    )

    def verifier(candidate: VectorIndex) -> bool:
        return False

    failing = KnowledgeReindexer(
        settings=settings,
        ingestor=make_ingestor(tmp_path),
        provider=FakeEmbeddingProvider(),
        verify_before_swap=verifier,
    )
    with pytest.raises(ReindexVerificationError):
        failing.run()

    assert index_pair_bytes(tmp_path) == before
    assert load_index(path=settings.vector_store_path).count == 2


def test_verification_exception_is_wrapped(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)

    def verifier(candidate: VectorIndex) -> bool:
        raise ValueError("verifier exploded")

    reindexer = KnowledgeReindexer(
        settings=settings,
        ingestor=make_ingestor(tmp_path),
        provider=FakeEmbeddingProvider(),
        verify_before_swap=verifier,
    )
    with pytest.raises(ReindexVerificationError, match="verifier exploded"):
        reindexer.run()
    assert not index_exists(path=settings.vector_store_path)


# --- 6. Async entry point and typed errors ----------------------------------


def test_async_reindex_entry_point(tmp_path: Path) -> None:
    build_corpus(tmp_path)
    settings = make_settings(tmp_path)
    reindexer = KnowledgeReindexer(
        settings=settings, ingestor=make_ingestor(tmp_path), provider=FakeEmbeddingProvider()
    )

    report = asyncio.run(reindexer.reindex())

    assert report.status == "completed"
    assert report.index_count == 2
    assert index_exists(path=settings.vector_store_path)


def test_typed_error_hierarchy() -> None:
    assert issubclass(ReindexEmptyError, ReindexError)
    assert issubclass(ReindexEmbeddingError, ReindexError)
    assert issubclass(ReindexVerificationError, ReindexError)

"""Knowledge re-indexing background job (IMPLEMENTATION_PLAN.md §4 RAG task 7).

Purpose:
    Orchestrate the complete RAG re-index pipeline — read → extract → validate
    → chunk → embed → index (AI_ARCHITECTURE.md §36.2) — as an idempotent,
    atomic background job that is never run on the request path
    (BACKEND_ARCHITECTURE.md §19; TESTING_STRATEGY.md §13.5). It composes the
    already-implemented Phase 9 tasks (ingestion/chunking, embeddings, FAISS
    index + persistence) and adds the re-index job semantics the architecture
    requires (AI_ARCHITECTURE.md §36.6-36.8).

Re-index policy (AI_ARCHITECTURE.md §36.7):
    - Trigger: content change (new checksum), metadata change, or a manual
      admin request — this job performs the work; the worker/scheduler that
      invokes it on those triggers is Phase 2 background-task infra.
    - Atomic swap: the new index is built fully in memory, optionally verified
      against a golden retrieval set (task 8; TESTING_STRATEGY.md §13.5), and
      only then persisted — ``save_index`` writes temp files, validates, and
      atomically replaces the live pair. The manifest is derived state and is
      written after the index.
    - Idempotency: re-running with no changes embeds nothing, swaps nothing,
      and reports ``status="unchanged"``. Unchanged documents (same checksum +
      version) are carried forward from the current index; only new or changed
      documents are re-embedded (AI_ARCHITECTURE.md §36.6).
    - Regenerability: the FAISS index is a cache (AI_ARCHITECTURE.md §36.7);
      the source of truth is ``knowledge/`` plus the SHA-256 checksums in
      ``knowledge/vectorstore/manifest.json``. A corrupt or incompatible index
      is therefore recovered by a full rebuild, never served stale.
    - Never clobber good data: an empty corpus raises ``ReindexEmptyError`` and
      never replaces a valid index; a failed verification aborts the swap.

Safety:
    This module never writes to the request path, never calls the LLM, and
    never touches the backend persistence layer — it is a pure
    ingest → embed → index job over ``knowledge/``, exactly as §36.2 and
    BACKEND_ARCHITECTURE.md §21.1 define.

Error handling:
    Every failure raises a typed ``ReindexError`` subclass. After any failure
    the previously persisted index is untouched (all persistence happens in the
    final two steps), so a failed re-index never leaves a partially-swapped
    index.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ai.core.config import Settings
from ai.rag.embeddings import (
    ChunkEmbedding,
    EmbeddingError,
    EmbeddingProvider,
    EmbeddingService,
    create_embedding_provider,
)
from ai.rag.faiss_index import (
    FaissIndexError,
    FaissUnavailableError,
    VectorIndex,
    build_index,
    index_exists,
    load_index,
    save_index,
)
from ai.rag.ingestion import IngestedDocument, IngestionError, KnowledgeIngestor

# Bump when the manifest format changes (loaders reject an unknown version).
MANIFEST_VERSION = 1
# Companion manifest storing the SHA-256 checksum per indexed source (§36.3).
MANIFEST_FILE_NAME = "manifest.json"


class ReindexError(Exception):
    """Base class for all knowledge re-indexing failures (§36.7)."""


class ReindexEmptyError(ReindexError):
    """No documents were discovered; a re-index would clobber the index."""


class ReindexIngestionError(ReindexError):
    """Document ingestion/validation failed (§36.2-36.3)."""


class ReindexEmbeddingError(ReindexError):
    """Chunk embedding failed (§15.1)."""


class ReindexIndexError(ReindexError):
    """Index build, load, or persistence failed (§15.2, §36.7)."""


class ReindexManifestError(ReindexError):
    """The re-index manifest could not be persisted."""


class ReindexVerificationError(ReindexError):
    """Golden retrieval-set verification failed; the swap was aborted (§13.5)."""


class ReindexReport(BaseModel):
    """The outcome of one re-index job run (§36.7)."""

    reindex_id: uuid.UUID
    status: Literal["completed", "unchanged"]
    started_at: datetime
    ended_at: datetime
    documents_found: int = Field(ge=0)
    documents_changed: int = Field(ge=0)
    documents_unchanged: int = Field(ge=0)
    chunks_embedded: int = Field(ge=0)
    chunks_carried_forward: int = Field(ge=0)
    index_count: int = Field(ge=0)
    index_path: str
    warnings: list[str] = Field(default_factory=list)


class KnowledgeReindexer:
    """The knowledge re-index background job (§36.2, §36.7, task 7).

    All collaborators are injectable so the job is fully testable and offline:
    a ``KnowledgeIngestor`` over a temp knowledge root, an ``EmbeddingService``
    (or its provider), and an optional ``verify_before_swap`` callable — the
    golden-set verifier built by ``ai.rag.evaluation.build_golden_verifier``
    (task 8). No client of any kind is constructed here — no LLM, no network,
    no database.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        ingestor: KnowledgeIngestor | None = None,
        provider: EmbeddingProvider | None = None,
        embedding_service: EmbeddingService | None = None,
        verify_before_swap: Callable[[VectorIndex], bool] | None = None,
    ) -> None:
        self.settings = settings
        self._ingestor = (
            ingestor if ingestor is not None else KnowledgeIngestor(settings.knowledge_root)
        )
        self._provider = provider
        self._embedding_service = embedding_service
        self._verify_before_swap = verify_before_swap

    def run(self) -> ReindexReport:
        """Run the re-index job synchronously and return its report.

        The job is safe to run from a script or a synchronous caller; the async
        ``reindex()`` entry point off-loads it so it never blocks the event
        loop (background job, BACKEND_ARCHITECTURE.md §19).
        """
        started = datetime.now(UTC)
        reindex_id = uuid.uuid4()
        index_path = Path(self.settings.vector_store_path)

        documents = self._ingest()
        previous_index, previous_manifest, warnings = self._load_previous(index_path)

        current = {
            document.source_path: {
                "checksum_sha256": document.checksum_sha256,
                "version": document.version,
            }
            for document in documents
        }
        changed, unchanged = self._plan_changes(
            documents, previous_index, previous_manifest, warnings
        )
        removed_sources = (
            {entry.source_path for entry in previous_index.entries} - set(current)
            if previous_index is not None
            else set()
        )
        if removed_sources:
            warnings.append(
                f"{len(removed_sources)} source(s) removed from the knowledge "
                "root; re-indexing to drop their chunks"
            )

        if previous_index is not None and not changed and not removed_sources:
            return ReindexReport(
                reindex_id=reindex_id,
                status="unchanged",
                started_at=started,
                ended_at=datetime.now(UTC),
                documents_found=len(documents),
                documents_changed=0,
                documents_unchanged=len(unchanged),
                chunks_embedded=0,
                chunks_carried_forward=previous_index.count,
                index_count=previous_index.count,
                index_path=str(index_path),
                warnings=warnings,
            )

        new_embeddings = self._embed_changed(changed) if changed else []
        carried = self._carry_forward(previous_index, documents, unchanged)

        merged = sorted(
            carried + list(new_embeddings),
            key=lambda entry: (entry.source_path, entry.chunk_index, entry.chunk_id),
        )
        new_index = self._build(merged)
        self._verify(new_index)

        self._persist(new_index, index_path, current)

        return ReindexReport(
            reindex_id=reindex_id,
            status="completed",
            started_at=started,
            ended_at=datetime.now(UTC),
            documents_found=len(documents),
            documents_changed=len(changed),
            documents_unchanged=len(unchanged),
            chunks_embedded=len(new_embeddings),
            chunks_carried_forward=len(carried),
            index_count=new_index.count,
            index_path=str(index_path),
            warnings=warnings,
        )

    async def reindex(self) -> ReindexReport:
        """Run the re-index job off the event loop (background-job entry point).

        A worker (Phase 2 background-task infra) invokes this; the synchronous
        pipeline runs in a worker thread so the event loop stays responsive
        (BACKEND_ARCHITECTURE.md §19).
        """
        return await asyncio.to_thread(self.run)

    # --- pipeline stages ----------------------------------------------------

    def _ingest(self) -> list[IngestedDocument]:
        """Stage 1-2 (§36.2): discover, read, validate, and chunk documents."""
        try:
            documents = self._ingestor.ingest_directory()
        except IngestionError as exc:
            raise ReindexIngestionError(f"knowledge ingestion failed: {exc}") from exc
        if not documents:
            raise ReindexEmptyError(
                "no documents found under the knowledge root; refusing to "
                "replace the current index with an empty one"
            )
        return documents

    def _load_previous(
        self, index_path: Path
    ) -> tuple[VectorIndex | None, dict[str, Any] | None, list[str]]:
        """Stage 3: read the current index and manifest, recording warnings.

        A missing index is a normal first run. A corrupt/incompatible index is
        treated as no index and recovered by a full rebuild (§36.7
        regenerability, §31.1 health-check recovery); a missing FAISS package
        aborts immediately (it is a dependency problem, not a data problem).
        """
        warnings: list[str] = []
        index: VectorIndex | None = None
        if index_exists(path=index_path):
            try:
                index = load_index(path=index_path)
            except FaissUnavailableError as exc:
                raise ReindexIndexError(
                    f"FAISS is unavailable; cannot load or rebuild the index: {exc}"
                ) from exc
            except FaissIndexError as exc:
                warnings.append(
                    f"existing index unreadable ({type(exc).__name__}); "
                    "recovering with a full rebuild"
                )
                index = None
        manifest = self._read_manifest(index_path, warnings)
        return index, manifest, warnings

    def _plan_changes(
        self,
        documents: list[IngestedDocument],
        previous_index: VectorIndex | None,
        previous_manifest: dict[str, Any] | None,
        warnings: list[str],
    ) -> tuple[list[IngestedDocument], set[str]]:
        """Change detection: new/changed documents vs. unchanged sources.

        A document is unchanged only when its SHA-256 checksum AND version both
        match the manifest (AI_ARCHITECTURE.md §36.3, §36.7 idempotency). When
        there is nothing to carry forward (no index, or no manifest to prove
        currency) every document is treated as changed so the index is rebuilt
        from the source of truth.
        """
        if previous_index is None:
            if previous_manifest is not None:
                warnings.append("manifest present but index missing; full re-embed")
            return list(documents), set()

        if previous_manifest is None:
            warnings.append("no previous re-index manifest; all documents re-embedded")
            return list(documents), set()

        changed: list[IngestedDocument] = []
        unchanged: set[str] = set()
        for document in documents:
            previous = previous_manifest.get(document.source_path)
            if (
                isinstance(previous, dict)
                and previous.get("checksum_sha256") == document.checksum_sha256
                and previous.get("version") == document.version
            ):
                unchanged.add(document.source_path)
            else:
                changed.append(document)
        return changed, unchanged

    def _embed_changed(self, changed: list[IngestedDocument]) -> list[ChunkEmbedding]:
        """Stage 4 (§15.1): embed only new/changed chunks."""
        chunks = [chunk for document in changed for chunk in document.chunks]
        try:
            return self._embedding().embed_chunks(chunks)
        except EmbeddingError as exc:
            raise ReindexEmbeddingError(f"chunk embedding failed: {exc}") from exc

    def _carry_forward(
        self,
        previous_index: VectorIndex | None,
        documents: list[IngestedDocument],
        unchanged: set[str],
    ) -> list[ChunkEmbedding]:
        """Stage 5 (§36.6): retain unchanged chunks from the current index.

        Unchanged chunks keep their existing vectors; sources no longer present
        in ``knowledge/`` are dropped (the index is a regenerable cache
        rebuilt from the source of truth, §36.7).
        """
        if previous_index is None:
            return []
        versions = {document.source_path: document.version for document in documents}
        return [
            entry
            for entry in previous_index.entries
            if entry.source_path in unchanged
            and versions.get(entry.source_path) == entry.version
        ]

    def _build(self, merged: list[ChunkEmbedding]) -> VectorIndex:
        """Stage 6 (§15.2): build the candidate index from merged embeddings."""
        try:
            return build_index(merged)
        except FaissIndexError as exc:
            raise ReindexIndexError(f"index build failed: {exc}") from exc

    def _verify(self, candidate: VectorIndex) -> None:
        """Stage 7 (§13.5): golden retrieval-set verification before the swap."""
        if self._verify_before_swap is None:
            return
        try:
            verified = self._verify_before_swap(candidate)
        except Exception as exc:
            raise ReindexVerificationError(
                f"golden-set verification failed: {exc}"
            ) from exc
        if not verified:
            raise ReindexVerificationError(
                "candidate index failed golden retrieval-set verification; "
                "atomic swap aborted (TESTING_STRATEGY.md §13.5)"
            )

    def _persist(
        self,
        new_index: VectorIndex,
        index_path: Path,
        manifest: dict[str, dict[str, str]],
    ) -> None:
        """Stage 8 (§36.7): atomic swap of the index, then the manifest.

        ``save_index`` writes temp files, validates, and atomically replaces the
        live index pair. The manifest is derived state persisted after the swap;
        a failure here leaves the new index live with a stale manifest, which
        the next run detects and recovers from (idempotent full re-embed).
        """
        try:
            save_index(new_index, path=index_path)
        except FaissIndexError as exc:
            raise ReindexIndexError(f"index persistence failed: {exc}") from exc
        try:
            self._write_manifest(index_path, manifest)
        except OSError as exc:
            raise ReindexManifestError(f"manifest persistence failed: {exc}") from exc

    def _write_manifest(
        self, index_path: Path, documents: dict[str, dict[str, str]]
    ) -> None:
        """Atomically persist the per-source checksum manifest."""
        payload: dict[str, Any] = {"version": MANIFEST_VERSION, "documents": documents}
        path = index_path / MANIFEST_FILE_NAME
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    def _read_manifest(
        self, index_path: Path, warnings: list[str]
    ) -> dict[str, Any] | None:
        """Read the manifest, or ``None`` when absent/unreadable (§36.7)."""
        path = index_path / MANIFEST_FILE_NAME
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(
                f"re-index manifest unreadable ({type(exc).__name__}); "
                "all documents re-embedded"
            )
            return None
        if (
            not isinstance(payload, dict)
            or payload.get("version") != MANIFEST_VERSION
            or not isinstance(payload.get("documents"), dict)
        ):
            warnings.append(
                "re-index manifest invalid or version mismatch; all documents re-embedded"
            )
            return None
        documents: dict[str, Any] = payload["documents"]
        return documents

    def _embedding(self) -> EmbeddingService:
        """Resolve the embedding service lazily (provider created on demand)."""
        service = self._embedding_service
        if service is not None:
            return service
        provider = self._provider
        if provider is None:
            provider = create_embedding_provider(self.settings)
            self._provider = provider
        service = EmbeddingService(provider=provider)
        self._embedding_service = service
        return service

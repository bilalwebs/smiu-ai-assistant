"""FAISS vector index build and persistence (AI_ARCHITECTURE.md §15.2, §16).

§15.2 fixes the store: the FAISS index lives under ``knowledge/vectorstore/``
(``Settings.vector_store_path``) and holds vectors only, keyed by position. A
companion ``metadata.json`` mapping preserves the one-to-one FAISS position ↔
``ChunkEmbedding`` ↔ ``chunk_id`` association so later retrieval (Phase 9,
task 4) can turn raw index hits back into ``RetrievedChunk`` records including
source metadata and the original chunk text (§16.1, §19.1). §36.7 keeps the
index a regenerable cache: it is built from ``knowledge/`` +
``knowledge_chunks``, is never the only store of knowledge, and is rebuilt
atomically (write temp files → validate → replace final files).

Similarity metric: the embedding model is a Sentence Transformers encoder
(§15.1) and §16.2 defines similarity by "the index's distance metric
(consistent with the embedding model)". This module therefore uses **cosine**
similarity implemented the standard FAISS way: vectors are L2-normalized at
build and query time and the index is an ``IndexFlatIP`` (inner product,
``METRIC_INNER_PRODUCT``), so the raw score equals the cosine similarity in
[-1, 1]. Raw scores are returned as-is (§16.3); ranking policy, thresholds,
category filtering and ``RetrievedChunk`` construction belong to the Retriever
(Phase 9, task 4) and are intentionally absent here.

Determinism: input order == FAISS position == metadata position, and identical
inputs produce byte-identical persisted files. The FAISS binary is written to a
temporary file, reloaded and validated against the metadata mapping, then
atomically replaced; metadata follows the same pattern. A load in the tiny gap
between the two replacements fails safely with ``MetadataMismatchError`` rather
than returning a partially-replaced index.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import math
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from ai.rag.embeddings import ChunkEmbedding

# Bump when the on-disk metadata format changes (load rejects older versions).
INDEX_VERSION = 1
# The similarity metric recorded with every persisted index (§16.2).
SIMILARITY_METRIC = "cosine"

_INDEX_FILE_NAME = "index.faiss"
_METADATA_FILE_NAME = "metadata.json"


class FaissIndexError(Exception):
    """Base class for all FAISS vector index errors (AI_ARCHITECTURE.md §15.2)."""


class FaissUnavailableError(FaissIndexError):
    """The faiss package is not installed or cannot be imported."""


class EmptyIndexInputError(FaissIndexError):
    """No embeddings were provided to build an index."""


class InvalidVectorError(FaissIndexError):
    """A vector is empty, non-finite, or has zero norm (not cosine-normalizable)."""


class IndexDimensionError(FaissIndexError):
    """Vector dimensions are inconsistent across the index or a query."""


class DuplicateChunkIdError(FaissIndexError):
    """Two embeddings in one index share the same ``chunk_id``."""


class ModelParityError(FaissIndexError):
    """Embeddings in one index use more than one embedding model (§15.1)."""


class IndexPersistenceError(FaissIndexError):
    """The index could not be written to or replaced on disk."""


class IndexLoadError(FaissIndexError):
    """The persisted index directory or one of its files is missing."""


class IndexVersionError(FaissIndexError):
    """The persisted index metadata version is not supported."""


class CorruptIndexError(FaissIndexError):
    """The persisted FAISS binary or metadata mapping is malformed."""


class MetadataMismatchError(FaissIndexError):
    """The FAISS binary and metadata mapping disagree (count/dimension/metric/model)."""


class VectorIndex:
    """An in-memory FAISS index plus its position-ordered metadata mapping.

    ``entries[position]`` is the ``ChunkEmbedding`` whose vector lives at FAISS
    position ``position``. ``search`` is the only low-level primitive exposed
    here: it returns raw (positions, cosine scores) pairs for a query vector and
    performs no retrieval policy — that is the Retriever's job (§16).
    """

    def __init__(
        self,
        *,
        index: Any,
        entries: list[ChunkEmbedding],
        metric: str,
        model_name: str,
        dimension: int,
    ) -> None:
        self._index = index
        self._entries = entries
        self.metric = metric
        self.model_name = model_name
        self.dimension = dimension

    @property
    def index(self) -> Any:
        """The underlying FAISS index object."""
        return self._index

    @property
    def entries(self) -> list[ChunkEmbedding]:
        """The metadata mapping, position-ordered (§15.2)."""
        return self._entries

    @property
    def count(self) -> int:
        """The number of indexed vectors."""
        return len(self._entries)

    def search(self, *, vector: Sequence[float], k: int) -> tuple[list[int], list[float]]:
        """Return ``(positions, scores)`` of the nearest neighbours.

        Scores are raw cosine similarities in [-1, 1] (§16.3); positions index
        into ``entries``. Returns at most ``k`` real hits in descending score
        order — FAISS's ``-1`` padding when ``k`` exceeds the index size is
        dropped. ``k`` is a bound, not a ranking policy.
        """
        if k <= 0:
            raise ValueError("k must be a positive integer")
        query = list(vector)
        if not query:
            raise InvalidVectorError("query vector must not be empty")
        if len(query) != self.dimension:
            raise IndexDimensionError(
                f"query vector dimension {len(query)} does not match index dimension "
                f"{self.dimension}"
            )
        for value in query:
            if not math.isfinite(value):
                raise InvalidVectorError("query vector contains non-finite values")
        normalized = _normalize(query, label="query vector")
        scores, positions = self._index.search(np.array([normalized], dtype=np.float32), k)
        hits = [
            (float(score), int(position))
            for score, position in zip(scores[0], positions[0], strict=True)
            if position >= 0
        ]
        return ([position for _score, position in hits], [score for score, _position in hits])


def build_index(embeddings: Sequence[ChunkEmbedding]) -> VectorIndex:
    """Build a cosine-similarity FAISS index from chunk embeddings (§15.2, §16).

    Input order is preserved: ``embeddings[i]`` maps to FAISS position ``i``.
    Vectors are validated (consistent dimension, finite values, non-zero norm)
    and L2-normalized before being stored in an ``IndexFlatIP``.
    """
    entries = list(embeddings)
    if not entries:
        raise EmptyIndexInputError(
            "at least one ChunkEmbedding is required to build an index"
        )
    for entry in entries:
        if not isinstance(entry, ChunkEmbedding):
            raise FaissIndexError(f"expected ChunkEmbedding, got {type(entry).__name__}")
    _reject_duplicate_chunk_ids(entries)

    dimension = entries[0].dimension
    if dimension == 0:
        raise InvalidVectorError("embedding vectors must not be empty")

    model_names = {entry.model_name for entry in entries}
    if len(model_names) > 1:
        raise ModelParityError(
            "all embeddings in one index must share a single model (§15.1 model "
            f"parity); got {', '.join(sorted(model_names))}"
        )
    model_name = entries[0].model_name

    matrix: list[list[float]] = []
    for entry in entries:
        if len(entry.vector) != dimension:
            raise IndexDimensionError(
                f"embedding '{entry.chunk_id}' has dimension {len(entry.vector)}, "
                f"expected {dimension}"
            )
        for value in entry.vector:
            if not math.isfinite(value):
                raise InvalidVectorError(
                    f"embedding '{entry.chunk_id}' contains non-finite values"
                )
        matrix.append(_normalize(entry.vector, label=f"embedding '{entry.chunk_id}' vector"))

    faiss_mod = _load_faiss()
    index = faiss_mod.IndexFlatIP(dimension)
    index.add(np.array(matrix, dtype=np.float32))
    return VectorIndex(
        index=index,
        entries=entries,
        metric=SIMILARITY_METRIC,
        model_name=model_name,
        dimension=dimension,
    )


def save_index(index: VectorIndex, *, path: str | Path) -> None:
    """Atomically persist the index + metadata mapping to ``path`` (§36.7).

    Writes ``index.faiss`` and ``metadata.json`` into ``path`` (created if
    needed) via temporary files that are reloaded and validated before being
    atomically replaced. On any failure the temporary files are removed and no
    partial output is left behind.
    """
    if not isinstance(index, VectorIndex):
        raise FaissIndexError(f"expected VectorIndex, got {type(index).__name__}")
    if index.metric != SIMILARITY_METRIC:
        raise FaissIndexError(
            f"cannot persist index with metric {index.metric!r}; expected "
            f"'{SIMILARITY_METRIC}'"
        )
    target = Path(path)
    if target.exists() and not target.is_dir():
        raise IndexPersistenceError(f"index path is not a directory: {target}")
    target.mkdir(parents=True, exist_ok=True)

    index_path = target / _INDEX_FILE_NAME
    metadata_path = target / _METADATA_FILE_NAME
    tmp_index = index_path.with_suffix(".faiss.tmp")
    tmp_metadata = metadata_path.with_suffix(".json.tmp")
    tmp_files = [tmp_index, tmp_metadata]

    try:
        faiss_mod = _load_faiss()
        faiss_mod.write_index(index.index, str(tmp_index))
        payload: dict[str, Any] = {
            "version": INDEX_VERSION,
            "metric": index.metric,
            "dimension": index.dimension,
            "model_name": index.model_name,
            "count": index.count,
            "entries": [entry.model_dump(mode="json") for entry in index.entries],
        }
        _write_json(tmp_metadata, payload)
        _validate_written(tmp_index, tmp_metadata, index)
        os.replace(tmp_index, index_path)
        os.replace(tmp_metadata, metadata_path)
    except FaissIndexError:
        _cleanup(tmp_files)
        raise
    except Exception as exc:
        _cleanup(tmp_files)
        raise IndexPersistenceError(
            f"failed to persist FAISS index to {target}: {exc}"
        ) from exc


def load_index(*, path: str | Path) -> VectorIndex:
    """Load a persisted index + metadata mapping from ``path``.

    Validates the metadata mapping (version, metric, count, dimension, model
    parity, per-entry structure) and cross-checks it against the FAISS binary
    (count, dimension, inner-product metric) before returning a ``VectorIndex``.
    """
    target = Path(path)
    if not target.exists() or not target.is_dir():
        raise IndexLoadError(f"index directory does not exist: {target}")
    index_path = target / _INDEX_FILE_NAME
    metadata_path = target / _METADATA_FILE_NAME
    if not index_path.is_file():
        raise IndexLoadError(f"FAISS index file is missing: {index_path}")
    if not metadata_path.is_file():
        raise IndexLoadError(f"index metadata file is missing: {metadata_path}")

    payload = _read_metadata(metadata_path)
    _validate_metadata_payload(payload)

    faiss_mod = _load_faiss()
    try:
        index = faiss_mod.read_index(str(index_path))
    except Exception as exc:
        raise CorruptIndexError(f"cannot load FAISS index {index_path}: {exc}") from exc

    count = int(payload["count"])
    dimension = int(payload["dimension"])
    entries = _decode_entries(payload["entries"])

    if int(index.ntotal) != count:
        raise MetadataMismatchError(
            f"FAISS index holds {int(index.ntotal)} vectors but metadata declares {count}"
        )
    if int(index.d) != dimension:
        raise MetadataMismatchError(
            f"FAISS index dimension {int(index.d)} does not match metadata {dimension}"
        )
    if int(index.metric_type) != faiss_mod.METRIC_INNER_PRODUCT:
        raise MetadataMismatchError(
            f"FAISS index uses metric {int(index.metric_type)}, expected inner "
            "product for cosine similarity"
        )

    return VectorIndex(
        index=index,
        entries=entries,
        metric=str(payload["metric"]),
        model_name=str(payload["model_name"]),
        dimension=dimension,
    )


def index_exists(*, path: str | Path) -> bool:
    """True when ``path`` holds a complete index + metadata pair."""
    target = Path(path)
    return (
        target.is_dir()
        and (target / _INDEX_FILE_NAME).is_file()
        and (target / _METADATA_FILE_NAME).is_file()
    )


def _reject_duplicate_chunk_ids(entries: Sequence[ChunkEmbedding]) -> None:
    seen: set[str] = set()
    for entry in entries:
        if entry.chunk_id in seen:
            raise DuplicateChunkIdError(
                f"duplicate chunk_id '{entry.chunk_id}' in index input"
            )
        seen.add(entry.chunk_id)


def _normalize(vector: Sequence[float], *, label: str) -> list[float]:
    values = np.array([float(value) for value in vector], dtype=np.float64)
    norm = float(np.linalg.norm(values))
    if norm == 0.0 or not math.isfinite(norm):
        raise InvalidVectorError(
            f"{label} cannot be normalized for cosine similarity (zero or non-finite norm)"
        )
    return [float(value / norm) for value in values]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _read_metadata(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CorruptIndexError(f"cannot read index metadata {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CorruptIndexError(f"index metadata {path} is not a JSON object")
    return payload


def _validate_metadata_payload(payload: dict[str, Any]) -> None:
    if "version" not in payload:
        raise CorruptIndexError("metadata is missing 'version'")
    if payload["version"] != INDEX_VERSION:
        raise IndexVersionError(
            f"index metadata version {payload['version']} is not supported "
            f"(expected {INDEX_VERSION})"
        )
    if payload.get("metric") != SIMILARITY_METRIC:
        raise MetadataMismatchError(
            f"index metric {payload.get('metric')!r} does not match expected "
            f"'{SIMILARITY_METRIC}'"
        )
    count = payload.get("count")
    if not isinstance(count, int) or count < 0:
        raise CorruptIndexError("metadata has an invalid 'count'")
    dimension = payload.get("dimension")
    if not isinstance(dimension, int) or dimension <= 0:
        raise CorruptIndexError("metadata has an invalid 'dimension'")
    model_name = payload.get("model_name")
    if not isinstance(model_name, str) or not model_name:
        raise CorruptIndexError("metadata has an invalid 'model_name'")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise CorruptIndexError("metadata 'entries' must be a list")
    if len(entries) != count:
        raise CorruptIndexError(
            f"metadata 'count' is {count} but {len(entries)} entries were found"
        )
    seen: set[str] = set()
    for position, record in enumerate(entries):
        if not isinstance(record, dict):
            raise CorruptIndexError(f"metadata entry {position} is not an object")
        for key in ("chunk_id", "title", "category", "version", "model_name", "vector"):
            if key not in record:
                raise CorruptIndexError(f"metadata entry {position} is missing '{key}'")
        chunk_id = record["chunk_id"]
        if not isinstance(chunk_id, str) or not chunk_id:
            raise CorruptIndexError(f"metadata entry {position} has an invalid 'chunk_id'")
        if chunk_id in seen:
            raise CorruptIndexError(f"metadata entry {position} duplicates chunk_id '{chunk_id}'")
        seen.add(chunk_id)
        vector = record["vector"]
        if not isinstance(vector, list) or not vector:
            raise CorruptIndexError(f"metadata entry {position} has an invalid 'vector'")
        if len(vector) != dimension:
            raise MetadataMismatchError(
                f"metadata entry {position} vector dimension {len(vector)} does not "
                f"match {dimension}"
            )
        for value in vector:
            if not (isinstance(value, int | float) and math.isfinite(float(value))):
                raise CorruptIndexError(
                    f"metadata entry {position} vector contains non-finite values"
                )
        if record.get("model_name") != model_name:
            raise MetadataMismatchError(
                f"metadata entry {position} model {record.get('model_name')!r} does not "
                f"match '{model_name}'"
            )


def _decode_entries(raw_entries: list[Any]) -> list[ChunkEmbedding]:
    try:
        return [ChunkEmbedding.model_validate(record) for record in raw_entries]
    except Exception as exc:
        raise CorruptIndexError(f"metadata contains an invalid ChunkEmbedding: {exc}") from exc


def _validate_written(index_path: Path, metadata_path: Path, expected: VectorIndex) -> None:
    """Reload a freshly written temp index and confirm it matches expectations."""
    faiss_mod = _load_faiss()
    reloaded = faiss_mod.read_index(str(index_path))
    if int(reloaded.ntotal) != expected.count:
        raise MetadataMismatchError(
            f"persisted index holds {int(reloaded.ntotal)} vectors, expected {expected.count}"
        )
    if int(reloaded.d) != expected.dimension:
        raise MetadataMismatchError(
            f"persisted index dimension {int(reloaded.d)} does not match {expected.dimension}"
        )
    if int(reloaded.metric_type) != faiss_mod.METRIC_INNER_PRODUCT:
        raise MetadataMismatchError(
            f"persisted index uses metric {int(reloaded.metric_type)}, expected inner product"
        )
    payload = _read_metadata(metadata_path)
    _validate_metadata_payload(payload)
    if int(payload["count"]) != expected.count:
        raise MetadataMismatchError(
            f"persisted metadata declares {int(payload['count'])} vectors, "
            f"expected {expected.count}"
        )


def _cleanup(paths: list[Path]) -> None:
    for path in paths:
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)


def _load_faiss() -> Any:
    """Return the faiss module, raising a clear error when it is unavailable."""
    if importlib.util.find_spec("faiss") is None:
        raise FaissUnavailableError(
            "FAISS is not installed; install the AI service requirements to build "
            "or load the vector index (AI_ARCHITECTURE.md §15.2)"
        )
    try:
        import faiss
    except ImportError as exc:
        raise FaissUnavailableError(f"failed to import faiss: {exc}") from exc
    return faiss

"""FAISS vector index build/persistence tests (AI_ARCHITECTURE.md §15.2, §16).

Offline by construction: synthetic vectors only — no Sentence Transformer
weights, no external services, no network access (TESTING_STRATEGY.md
§12.1-12.4). Covers the Phase 9 task 3 requirements: build, index type/metric,
chunk↔position mapping, metadata preservation, persistence, load/validation,
error handling and determinism.
"""

from __future__ import annotations

import importlib
import json
import uuid
from pathlib import Path

import pytest

from ai.rag import faiss_index as faiss_index_module
from ai.rag.embeddings import ChunkEmbedding
from ai.rag.faiss_index import (
    CorruptIndexError,
    DuplicateChunkIdError,
    EmptyIndexInputError,
    FaissIndexError,
    FaissUnavailableError,
    IndexDimensionError,
    IndexLoadError,
    IndexPersistenceError,
    IndexVersionError,
    InvalidVectorError,
    MetadataMismatchError,
    ModelParityError,
    VectorIndex,
    build_index,
    index_exists,
    load_index,
    save_index,
)

MODEL_NAME = "fake/sentence-model"


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
    chunk_text: str = "Some admission text.",
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
        chunk_text=chunk_text,
        vector=vector,
    )


def sample_embeddings() -> list[ChunkEmbedding]:
    """Deterministic 4-dim vectors; position order = c1..c4 (§15.2)."""
    return [
        make_embedding("c1", [1.0, 0.0, 0.0, 0.0], chunk_index=0, chunk_text="First chunk."),
        make_embedding("c2", [0.0, 1.0, 0.0, 0.0], chunk_index=1, chunk_text="Second chunk."),
        make_embedding("c3", [0.5, 0.5, 0.0, 0.0], chunk_index=2, chunk_text="Third chunk."),
        make_embedding("c4", [-1.0, 0.0, 0.0, 0.0], chunk_index=3, chunk_text="Fourth chunk."),
    ]


def read_metadata(path: Path) -> dict:
    with (path / "metadata.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_metadata(path: Path, payload: dict) -> None:
    with (path / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def save_sample(path: Path) -> VectorIndex:
    index = build_index(sample_embeddings())
    save_index(index, path=path)
    return index


# --- 1. Dependency / import behavior -------------------------------------


def test_module_imports_and_exposes_version_metadata() -> None:
    assert faiss_index_module.INDEX_VERSION == 1
    assert faiss_index_module.SIMILARITY_METRIC == "cosine"


def test_faiss_dependency_is_importable() -> None:
    import faiss

    assert hasattr(faiss, "IndexFlatIP")
    assert hasattr(faiss, "METRIC_INNER_PRODUCT")


def test_missing_faiss_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, package: object = None) -> object:
        if name == "faiss":
            return None
        return real_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    with pytest.raises(FaissUnavailableError, match="FAISS is not installed"):
        build_index(sample_embeddings())


def test_module_has_no_network_imports() -> None:
    for name in ("requests", "httpx", "socket", "urllib"):
        assert name not in faiss_index_module.__dict__


# --- 2. Build -------------------------------------------------------------


def test_build_returns_vector_index() -> None:
    index = build_index(sample_embeddings())
    assert isinstance(index, VectorIndex)


def test_build_vector_count_matches_input() -> None:
    index = build_index(sample_embeddings())
    assert index.count == 4
    assert len(index.entries) == 4


def test_build_index_dimension_matches_embeddings() -> None:
    index = build_index(sample_embeddings())
    assert index.dimension == 4


def test_build_index_type_is_flat_ip() -> None:
    import faiss

    index = build_index(sample_embeddings())
    assert isinstance(index.index, faiss.IndexFlatIP)


def test_build_uses_inner_product_for_cosine() -> None:
    import faiss

    index = build_index(sample_embeddings())
    assert index.metric == "cosine"
    assert int(index.index.metric_type) == int(faiss.METRIC_INNER_PRODUCT)


def test_build_preserves_input_order_as_faiss_positions() -> None:
    index = build_index(sample_embeddings())
    assert [entry.chunk_id for entry in index.entries] == ["c1", "c2", "c3", "c4"]


def test_chunk_id_maps_to_faiss_position_via_search() -> None:
    index = build_index(sample_embeddings())
    positions, _scores = index.search(vector=[0.5, 0.5, 0.0, 0.0], k=4)
    assert positions[0] == 2
    assert index.entries[positions[0]].chunk_id == "c3"
    assert set(positions[:3]) == {0, 1, 2}


def test_build_preserves_source_metadata() -> None:
    doc_id = uuid.uuid4()
    embeddings = [
        make_embedding(
            "c1",
            [1.0, 0.0, 0.0, 0.0],
            document_id=doc_id,
            title="Merit List",
            category="examination",
            version="2",
            source_path="knowledge/examination/merit.md",
            chunk_index=7,
            heading="Merit Calculation",
            chunk_text="Merit is computed from aggregate marks.",
        )
    ]
    index = build_index(embeddings)
    record = index.entries[0]
    assert record.chunk_id == "c1"
    assert record.document_id == doc_id
    assert record.title == "Merit List"
    assert record.category == "examination"
    assert record.version == "2"
    assert record.source_path == "knowledge/examination/merit.md"
    assert record.chunk_index == 7
    assert record.heading == "Merit Calculation"
    assert record.model_name == MODEL_NAME
    assert record.chunk_text == "Merit is computed from aggregate marks."
    assert record.dimension == 4


# --- 3. Search primitive (no retrieval policy) ----------------------------


def test_search_returns_raw_cosine_scores_descending() -> None:
    index = build_index(sample_embeddings())
    positions, scores = index.search(vector=[1.0, 0.0, 0.0, 0.0], k=4)
    assert positions == [0, 2, 1, 3]
    assert scores == pytest.approx([1.0, 1.0 / 2**0.5, 0.0, -1.0])


def test_search_k_bounds_results_and_clamps_to_index_size() -> None:
    index = build_index(sample_embeddings())
    positions, scores = index.search(vector=[1.0, 0.0, 0.0, 0.0], k=2)
    assert positions == [0, 2]
    assert scores == pytest.approx([1.0, 1.0 / 2**0.5])
    positions, _scores = index.search(vector=[1.0, 0.0, 0.0, 0.0], k=10)
    assert len(positions) == 4


def test_search_scores_stay_within_cosine_range() -> None:
    index = build_index(sample_embeddings())
    _positions, scores = index.search(vector=[1.0, 0.0, 0.0, 0.0], k=4)
    assert all(-1.0 <= score <= 1.0 for score in scores)


def test_search_validates_inputs() -> None:
    index = build_index(sample_embeddings())
    with pytest.raises(ValueError, match="k must be a positive integer"):
        index.search(vector=[1.0, 0.0, 0.0, 0.0], k=0)
    with pytest.raises(InvalidVectorError, match="must not be empty"):
        index.search(vector=[], k=2)
    with pytest.raises(IndexDimensionError, match="dimension"):
        index.search(vector=[1.0, 0.0, 0.0], k=2)
    with pytest.raises(InvalidVectorError, match="non-finite"):
        index.search(vector=[float("nan"), 0.0, 0.0, 0.0], k=2)
    with pytest.raises(InvalidVectorError, match="zero or non-finite norm"):
        index.search(vector=[0.0, 0.0, 0.0, 0.0], k=2)


# --- 4. Build validation ---------------------------------------------------


def test_build_rejects_empty_input() -> None:
    with pytest.raises(EmptyIndexInputError, match="at least one"):
        build_index([])


def test_build_rejects_inconsistent_dimensions() -> None:
    embeddings = [
        make_embedding("c1", [1.0, 0.0, 0.0, 0.0]),
        make_embedding("c2", [0.0, 1.0, 0.0]),
    ]
    with pytest.raises(IndexDimensionError, match="c2"):
        build_index(embeddings)


def test_build_rejects_non_finite_vectors() -> None:
    with pytest.raises(InvalidVectorError, match="non-finite"):
        build_index([make_embedding("c1", [float("nan"), 0.0, 0.0, 0.0])])
    with pytest.raises(InvalidVectorError, match="non-finite"):
        build_index([make_embedding("c1", [1.0, float("inf"), 0.0, 0.0])])


def test_build_rejects_duplicate_chunk_ids() -> None:
    embeddings = [
        make_embedding("c1", [1.0, 0.0, 0.0, 0.0]),
        make_embedding("c1", [0.0, 1.0, 0.0, 0.0]),
    ]
    with pytest.raises(DuplicateChunkIdError, match="c1"):
        build_index(embeddings)


def test_build_rejects_mixed_embedding_models() -> None:
    embeddings = [
        make_embedding("c1", [1.0, 0.0, 0.0, 0.0], model_name="model-a"),
        make_embedding("c2", [0.0, 1.0, 0.0, 0.0], model_name="model-b"),
    ]
    with pytest.raises(ModelParityError, match="model"):
        build_index(embeddings)


def test_build_rejects_zero_norm_vector() -> None:
    with pytest.raises(InvalidVectorError, match="zero or non-finite norm"):
        build_index([make_embedding("c1", [0.0, 0.0, 0.0, 0.0])])


def test_build_rejects_non_embedding_objects() -> None:
    with pytest.raises(FaissIndexError, match="expected ChunkEmbedding"):
        build_index(["not an embedding"])  # type: ignore[arg-type]


# --- 5. Persistence ---------------------------------------------------------


def test_save_writes_index_and_metadata_files(tmp_path: Path) -> None:
    save_sample(tmp_path)
    assert (tmp_path / "index.faiss").is_file()
    assert (tmp_path / "metadata.json").is_file()
    assert index_exists(path=tmp_path)


def test_save_creates_missing_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "vectorstore"
    save_sample(target)
    assert (target / "index.faiss").is_file()


def test_save_rejects_file_path(tmp_path: Path) -> None:
    file_path = tmp_path / "a-file"
    file_path.write_text("not a directory", encoding="utf-8")
    with pytest.raises(IndexPersistenceError, match="not a directory"):
        save_index(build_index(sample_embeddings()), path=file_path)


def test_save_rejects_wrong_metric_metadata(tmp_path: Path) -> None:
    index = build_index(sample_embeddings())
    foreign = VectorIndex(
        index=index.index,
        entries=index.entries,
        metric="l2",
        model_name=index.model_name,
        dimension=index.dimension,
    )
    with pytest.raises(FaissIndexError, match="metric"):
        save_index(foreign, path=tmp_path)


def test_save_leaves_no_temp_files_on_success(tmp_path: Path) -> None:
    save_sample(tmp_path)
    assert not [p for p in tmp_path.iterdir() if ".tmp" in p.name]


def test_deterministic_persistence(tmp_path: Path) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"
    save_sample(first)
    save_sample(second)
    assert (first / "index.faiss").read_bytes() == (second / "index.faiss").read_bytes()
    assert (first / "metadata.json").read_bytes() == (second / "metadata.json").read_bytes()


# --- 6. Load ----------------------------------------------------------------


def test_load_returns_index_with_count(tmp_path: Path) -> None:
    save_sample(tmp_path)
    loaded = load_index(path=tmp_path)
    assert loaded.count == 4
    assert len(loaded.entries) == 4


def test_load_preserves_dimension(tmp_path: Path) -> None:
    save_sample(tmp_path)
    loaded = load_index(path=tmp_path)
    assert loaded.dimension == 4


def test_load_preserves_metadata_identical_to_original(tmp_path: Path) -> None:
    original = save_sample(tmp_path)
    loaded = load_index(path=tmp_path)
    assert loaded.entries == original.entries
    assert loaded.model_name == MODEL_NAME
    assert loaded.metric == "cosine"
    assert loaded.entries[0].chunk_text == "First chunk."


def test_load_preserves_position_ordering(tmp_path: Path) -> None:
    save_sample(tmp_path)
    loaded = load_index(path=tmp_path)
    assert [entry.chunk_id for entry in loaded.entries] == ["c1", "c2", "c3", "c4"]


def test_round_trip_search_matches_original(tmp_path: Path) -> None:
    original = save_sample(tmp_path)
    loaded = load_index(path=tmp_path)
    q = [1.0, 0.0, 0.0, 0.0]
    assert loaded.search(vector=q, k=4) == original.search(vector=q, k=4)


def test_load_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(IndexLoadError, match="does not exist"):
        load_index(path=tmp_path / "missing")


def test_load_missing_index_file(tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)
    write_metadata(tmp_path, {"version": 1})
    with pytest.raises(IndexLoadError, match="index file is missing"):
        load_index(path=tmp_path)


def test_load_missing_metadata_file(tmp_path: Path) -> None:
    save_sample(tmp_path)
    (tmp_path / "metadata.json").unlink()
    with pytest.raises(IndexLoadError, match="metadata file is missing"):
        load_index(path=tmp_path)


def test_load_corrupted_index_binary(tmp_path: Path) -> None:
    save_sample(tmp_path)
    (tmp_path / "index.faiss").write_bytes(b"this is not a faiss index")
    with pytest.raises(CorruptIndexError, match="cannot load FAISS index"):
        load_index(path=tmp_path)


def test_load_corrupted_metadata_json(tmp_path: Path) -> None:
    save_sample(tmp_path)
    (tmp_path / "metadata.json").write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(CorruptIndexError, match="cannot read index metadata"):
        load_index(path=tmp_path)


def test_load_incompatible_metadata_version(tmp_path: Path) -> None:
    save_sample(tmp_path)
    payload = read_metadata(tmp_path)
    payload["version"] = 999
    write_metadata(tmp_path, payload)
    with pytest.raises(IndexVersionError, match="version 999"):
        load_index(path=tmp_path)


def test_load_rejects_wrong_metric_in_metadata(tmp_path: Path) -> None:
    save_sample(tmp_path)
    payload = read_metadata(tmp_path)
    payload["metric"] = "l2"
    write_metadata(tmp_path, payload)
    with pytest.raises(MetadataMismatchError, match="metric"):
        load_index(path=tmp_path)


def test_load_rejects_entries_count_mismatch(tmp_path: Path) -> None:
    save_sample(tmp_path)
    payload = read_metadata(tmp_path)
    payload["entries"].pop(0)
    write_metadata(tmp_path, payload)
    with pytest.raises(CorruptIndexError, match="4 but 3 entries"):
        load_index(path=tmp_path)


def test_load_rejects_duplicate_chunk_ids_in_metadata(tmp_path: Path) -> None:
    save_sample(tmp_path)
    payload = read_metadata(tmp_path)
    payload["entries"][3]["chunk_id"] = "c1"
    write_metadata(tmp_path, payload)
    with pytest.raises(CorruptIndexError, match="duplicates chunk_id 'c1'"):
        load_index(path=tmp_path)


def test_load_rejects_index_metadata_count_mismatch(tmp_path: Path) -> None:
    save_sample(tmp_path)
    payload = read_metadata(tmp_path)
    payload["count"] = 2
    payload["entries"] = payload["entries"][:2]
    write_metadata(tmp_path, payload)
    with pytest.raises(MetadataMismatchError, match="4 vectors but metadata declares 2"):
        load_index(path=tmp_path)


def test_load_rejects_entry_vector_dimension_mismatch(tmp_path: Path) -> None:
    save_sample(tmp_path)
    payload = read_metadata(tmp_path)
    payload["entries"][0]["vector"] = [1.0, 0.0, 0.0]
    write_metadata(tmp_path, payload)
    with pytest.raises(MetadataMismatchError, match="dimension"):
        load_index(path=tmp_path)


def test_load_rejects_missing_chunk_text_in_metadata(tmp_path: Path) -> None:
    save_sample(tmp_path)
    payload = read_metadata(tmp_path)
    del payload["entries"][0]["chunk_text"]
    write_metadata(tmp_path, payload)
    with pytest.raises(CorruptIndexError, match="invalid ChunkEmbedding"):
        load_index(path=tmp_path)


def test_index_exists_false_for_partial_directory(tmp_path: Path) -> None:
    save_sample(tmp_path)
    (tmp_path / "metadata.json").unlink()
    assert not index_exists(path=tmp_path)

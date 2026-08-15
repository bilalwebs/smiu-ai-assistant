"""Document ingestion & chunking tests (Phase 9 RAG, task 1).

Sources: IMPLEMENTATION_PLAN.md §4 RAG task 1; AI_ARCHITECTURE.md §14.2
(Ingest → Validate → Chunk), §36.2 (ingestion), §36.3 (validation: file-type
whitelist, SHA-256 checksum, content scan, category), §36.4 (chunking:
semantic/size-bounded unit, overlap, determinism, heading/page metadata),
§36.5 (metadata structure); DATABASE_DESIGN.md §21.1 (§36.5 metadata fields,
partial-unique ``(source_path, version)``), §21.2 (chunk fields), §21.3
(only ``is_active`` + ``status='processed'`` current-version documents are
retrieval candidates); TESTING_STRATEGY.md §12.1.

All behavior is deterministic and offline: no embedding model, no FAISS, no
vector store, no LLM, no API, no database, and no network call is made. The
pdf/docx code paths are exercised through a monkeypatched
``importlib.util.find_spec`` so the tests never require the optional parser
packages (AI_ARCHITECTURE.md §36.3).
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

from ai.core.state import RetrievedChunk
from ai.rag.ingestion import (
    DocumentChunk,
    DocumentParseError,
    DuplicateSourceError,
    EmptyDocumentError,
    IngestedDocument,
    IngestionError,
    InvalidMetadataError,
    KnowledgeCategory,
    KnowledgeIngestor,
    MalformedDocumentError,
    UnsupportedFileTypeError,
    checksum_sha256,
    chunk_text,
    extract_text,
    ingest_document,
    ingest_documents,
    normalize_text,
    parse_document_header,
    validate_category,
    validate_version,
)

SAMPLE_TEXT = """# Admission Policy

Applicants need 60% in intermediate to be eligible.

The application window opens in March.

## Documents Required

A CNIC copy and a passport photo are required.
"""


def _ingest(**overrides: Any) -> IngestedDocument:
    kwargs: dict[str, Any] = {
        "text": SAMPLE_TEXT,
        "title": "Admission Policy",
        "category": "admission",
        "version": "1",
        "source_path": "admission/policy.md",
        "author": "admissions@example.com",
        "file_type": "md",
    }
    kwargs.update(overrides)
    return ingest_document(**kwargs)


# --- 1. Valid ingestion ------------------------------------------------


def test_valid_ingestion_produces_processed_document() -> None:
    document = _ingest()
    assert document.title == "Admission Policy"
    assert document.category == "admission"
    assert document.status == "processed"
    assert document.is_active is True
    assert document.chunk_count == len(document.chunks) >= 1


def test_valid_ingestion_checksum_is_sha256_of_normalized_text() -> None:
    expected = hashlib.sha256(normalize_text(SAMPLE_TEXT).encode("utf-8")).hexdigest()
    assert _ingest().checksum_sha256 == expected
    assert len(_ingest().checksum_sha256) == 64


# --- 2. Validation -----------------------------------------------------


def test_ingestion_validates_title_category_and_version() -> None:
    with pytest.raises(InvalidMetadataError):
        _ingest(title="   ")
    with pytest.raises(InvalidMetadataError):
        _ingest(category="not-a-category")
    with pytest.raises(InvalidMetadataError):
        _ingest(version="v2-beta")


def test_file_type_whitelist_is_enforced() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        _ingest(file_type="exe")
    with pytest.raises(UnsupportedFileTypeError):
        extract_text("policy.exe")


# --- 3. Empty rejection ------------------------------------------------


def test_empty_document_is_rejected() -> None:
    with pytest.raises(EmptyDocumentError):
        ingest_document(text="", title="Empty", category="faq")
    with pytest.raises(EmptyDocumentError):
        ingest_document(text="   \n\n  ", title="Blank", category="faq")


def test_extract_text_rejects_blank_source(tmp_path: Path) -> None:
    source = tmp_path / "blank.txt"
    source.write_text("  \n\n  ", encoding="utf-8")
    with pytest.raises(EmptyDocumentError):
        extract_text(str(source))


# --- 4. Unsupported rejection ------------------------------------------


def test_extract_text_rejects_unsupported_extension(tmp_path: Path) -> None:
    source = tmp_path / "notes.docx.exe"
    source.write_text("x", encoding="utf-8")
    with pytest.raises(UnsupportedFileTypeError):
        extract_text(str(source))


# --- 5. Malformed handling ---------------------------------------------


def test_extract_text_rejects_invalid_utf8(tmp_path: Path) -> None:
    source = tmp_path / "broken.txt"
    source.write_bytes(b"\xff\xfe not utf8 \x00")
    with pytest.raises(MalformedDocumentError):
        extract_text(str(source))


# --- 6. Category validation --------------------------------------------


def test_category_coercion_accepts_only_known_categories() -> None:
    for category in KnowledgeCategory:
        assert validate_category(category.value) == category.value
    with pytest.raises(InvalidMetadataError):
        validate_category("admissions")
    with pytest.raises(InvalidMetadataError):
        validate_category("")


# --- 7. Version validation ---------------------------------------------


def test_version_validation_accepts_dotted_integers_only() -> None:
    assert validate_version("1") == "1"
    assert validate_version("1.2") == "1.2"
    assert validate_version("2.0.1") == "2.0.1"
    for bad in ("", "  ", "v1", "1.0-beta", "1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0"):
        with pytest.raises(InvalidMetadataError):
            validate_version(bad)


# --- 8/9. Deterministic chunk ids + ordering ---------------------------


def test_chunk_ids_are_deterministic_across_calls() -> None:
    first = _ingest()
    second = _ingest()
    assert [c.chunk_id for c in first.chunks] == [c.chunk_id for c in second.chunks]
    assert first.checksum_sha256 == second.checksum_sha256


def test_chunk_ids_are_stable_per_source_version_position() -> None:
    document = _ingest()
    assert len({c.chunk_id for c in document.chunks}) == document.chunk_count
    assert document.chunks[0].chunk_id != document.chunks[1].chunk_id


def test_chunk_ordering_is_deterministic() -> None:
    first = _ingest()
    second = _ingest()
    assert [c.chunk_text for c in first.chunks] == [c.chunk_text for c in second.chunks]


# --- 10. Chunk boundaries ----------------------------------------------


def test_chunks_are_size_bounded_without_duplicated_paragraphs() -> None:
    big_paragraph = " ".join(f"sentence {index} " + "word " * 40 for index in range(30))
    chunks = chunk_text(text=big_paragraph, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    assert all(len(text) <= 200 + 40 + 1 for text, _ in chunks)
    for index, (text, _) in enumerate(chunks[1:], start=1):
        previous = chunks[index - 1][0]
        assert previous not in text


def test_chunk_size_and_overlap_constraints() -> None:
    with pytest.raises(ValueError):
        chunk_text(text="x" * 10, chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text(text="x" * 10, chunk_size=10, overlap=-1)


# --- 11. Chunk metadata -------------------------------------------------


def test_chunk_carries_heading_token_and_character_metadata() -> None:
    document = _ingest()
    first = document.chunks[0]
    assert first.heading is None or first.heading == "Admission Policy"
    assert first.token_count >= 1
    assert first.character_count == len(first.chunk_text)
    assert first.checksum_sha256 == document.checksum_sha256


def test_markdown_headings_attach_to_following_chunks() -> None:
    chunks = chunk_text(text=SAMPLE_TEXT, chunk_size=200, overlap=0)
    headings = [heading for _, heading in chunks]
    assert any(heading == "Admission Policy" for heading in headings)
    assert any(heading == "Documents Required" for heading in headings)


# --- 12. Source metadata ------------------------------------------------


def test_source_metadata_is_preserved_on_document_and_chunks() -> None:
    document = _ingest(source_path="admission/policy.md", file_size=1024)
    assert document.source_path == "admission/policy.md"
    assert document.file_size == 1024
    for chunk in document.chunks:
        assert chunk.source_path == "admission/policy.md"
        assert chunk.document_id == document.document_id


def test_file_size_validation() -> None:
    with pytest.raises(ValueError):
        _ingest(file_size=-1)


# --- 13. Category/version preservation ----------------------------------


def test_category_and_version_are_preserved_through_chunking() -> None:
    document = _ingest(category="examination", version="2.1")
    assert document.category == "examination"
    assert document.version == "2.1"
    for chunk in document.chunks:
        assert chunk.category == "examination"
        assert chunk.version == "2.1"


# --- 14. Chunk position -------------------------------------------------


def test_chunk_index_sequences_from_zero() -> None:
    document = _ingest()
    assert [c.chunk_index for c in document.chunks] == list(
        range(document.chunk_count)
    )


def test_chunk_position_is_unique_within_document() -> None:
    document = _ingest()
    assert len({c.chunk_index for c in document.chunks}) == document.chunk_count


# --- 15. Repeated ingestion identical -----------------------------------


def test_repeated_ingestion_is_identical() -> None:
    fixed_id = uuid.uuid4()
    first = _ingest(document_id=fixed_id)
    second = _ingest(document_id=fixed_id)
    assert first.model_dump() == second.model_dump()
    assert [c.model_dump() for c in first.chunks] == [
        c.model_dump() for c in second.chunks
    ]


# --- 16. Eligibility (pending/inactive/non-current) ---------------------


def test_eligible_document_accepts_current_version() -> None:
    document = _ingest()
    assert document.is_eligible(current_version="1") is True
    assert document.is_eligible() is True


def test_inactive_document_is_not_a_retrieval_candidate() -> None:
    document = _ingest()
    document.is_active = False
    assert document.is_eligible(current_version="1") is False


def test_non_processed_document_is_not_a_retrieval_candidate() -> None:
    document = _ingest()
    document.status = "pending"
    assert document.is_eligible(current_version="1") is False


def test_non_current_version_is_not_a_retrieval_candidate() -> None:
    document = _ingest(version="1")
    assert document.is_eligible(current_version="2") is False


# --- 17. RetrievedChunk compatibility -----------------------------------


def test_chunk_maps_to_retrieved_chunk_contract() -> None:
    document = _ingest()
    chunk = document.chunks[0]
    retrieved = chunk.to_retrieved_chunk(score=0.91)
    assert isinstance(retrieved, RetrievedChunk)
    assert retrieved.chunk_id == chunk.chunk_id
    assert retrieved.document_id == chunk.document_id
    assert retrieved.title == chunk.title
    assert retrieved.category == chunk.category
    assert retrieved.snippet == chunk.chunk_text
    assert retrieved.score == 0.91


# --- 18. Duplicate (source_path, version) rejection ---------------------


def test_duplicate_source_version_raises_duplicate_error() -> None:
    with pytest.raises(DuplicateSourceError):
        ingest_documents(
            [
                {"text": SAMPLE_TEXT, "title": "A", "category": "faq",
                 "version": "1", "source_path": "faq/a.md"},
                {"text": SAMPLE_TEXT, "title": "B", "category": "faq",
                 "version": "1", "source_path": "faq/a.md"},
            ]
        )


def test_same_source_different_version_is_allowed() -> None:
    documents = ingest_documents(
        [
            {"text": SAMPLE_TEXT, "title": "A", "category": "faq",
             "version": "1", "source_path": "faq/a.md"},
            {"text": SAMPLE_TEXT, "title": "A", "category": "faq",
             "version": "2", "source_path": "faq/a.md"},
        ]
    )
    assert [document.version for document in documents] == ["1", "2"]


# --- Front matter (header metadata, §36.5) ------------------------------


def test_front_matter_parses_title_category_version_author() -> None:
    text = (
        "---\n"
        "title: Examination Schedule\n"
        "category: examination\n"
        "version: 1.2\n"
        "author: Exam Office\n"
        "---\n"
        "The mid-term exam starts on 20 October."
    )
    metadata, body = parse_document_header(text)
    assert metadata == {
        "title": "Examination Schedule",
        "category": "examination",
        "version": "1.2",
        "author": "Exam Office",
    }
    assert body == "The mid-term exam starts on 20 October."


def test_front_matter_rejects_unknown_key() -> None:
    with pytest.raises(InvalidMetadataError):
        parse_document_header("---\nlanguage: ur\n---\nbody")


def test_front_matter_rejects_duplicate_key() -> None:
    with pytest.raises(InvalidMetadataError):
        parse_document_header("---\ntitle: A\ntitle: B\n---\nbody")


def test_front_matter_rejects_empty_value_and_unterminated_block() -> None:
    with pytest.raises(InvalidMetadataError):
        parse_document_header("---\ntitle:\n---\nbody")
    with pytest.raises(InvalidMetadataError):
        parse_document_header("---\ntitle: A\nbody")


def test_document_without_front_matter_returns_empty_metadata() -> None:
    metadata, body = parse_document_header("Just a plain document.")
    assert metadata == {}
    assert body == "Just a plain document."


# --- KnowledgeIngestor (directory ingestion, §36.2) ---------------------


def test_ingestor_discovers_and_ingests_category_folders(
    tmp_path: Path,
) -> None:
    for folder in ("admission", "faq"):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "admission" / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / "admission" / "policy.md").write_text(SAMPLE_TEXT, encoding="utf-8")
    (tmp_path / "faq" / "faqs.txt").write_text(
        "The office is open 9 am to 5 pm.", encoding="utf-8"
    )

    ingestor = KnowledgeIngestor(tmp_path)
    assert [path.name for path in ingestor.discover()] == ["policy.md", "faqs.txt"]

    documents = ingestor.ingest_directory()
    assert [document.source_path for document in documents] == [
        "admission/policy.md",
        "faq/faqs.txt",
    ]
    assert documents[0].category == "admission"
    assert documents[1].category == "faq"


def test_ingestor_ignores_documents_outside_category_folders(
    tmp_path: Path,
) -> None:
    (tmp_path / "admission").mkdir()
    (tmp_path / "misc").mkdir()
    (tmp_path / "admission" / "policy.md").write_text(SAMPLE_TEXT, encoding="utf-8")
    (tmp_path / "misc" / "note.md").write_text("hi", encoding="utf-8")

    ingestor = KnowledgeIngestor(tmp_path)
    assert [path.name for path in ingestor.discover()] == ["policy.md"]
    documents = ingestor.ingest_directory()
    assert [document.source_path for document in documents] == ["admission/policy.md"]


# --- pdf/docx determinism (monkeypatched parsers, §36.3) ----------------


def test_pdf_without_parser_raises_document_parse_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: None if name == "pypdf" else importlib.util.find_spec(name),
    )
    source = tmp_path / "doc.pdf"
    source.write_bytes(b"%PDF-1.4")
    with pytest.raises(DocumentParseError):
        extract_text(str(source))


def test_docx_without_parser_raises_document_parse_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: None if name == "docx" else importlib.util.find_spec(name),
    )
    source = tmp_path / "doc.docx"
    source.write_bytes(b"PK")
    with pytest.raises(DocumentParseError):
        extract_text(str(source))


def test_pdf_extraction_uses_installed_parser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    extracted = ["Page one text.", "Page two text."]

    class FakeReader:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.pages = [FakePage(text) for text in extracted]

    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    monkeypatch.setattr(
        importlib.util, "find_spec", lambda name: object() if name == "pypdf" else None
    )
    monkeypatch.setitem(
        sys.modules,
        "pypdf",
        type("pypdf", (), {"PdfReader": FakeReader}),
    )

    source = tmp_path / "doc.pdf"
    source.write_bytes(b"%PDF-1.4 placeholder")
    assert extract_text(str(source)) == "Page one text.\nPage two text."


def test_docx_extraction_uses_installed_parser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paragraphs = ["Heading", "Body paragraph."]

    class FakeDocument:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.paragraphs = [type("P", (), {"text": text}) for text in paragraphs]

    monkeypatch.setattr(
        importlib.util, "find_spec", lambda name: object() if name == "docx" else None
    )
    monkeypatch.setitem(
        sys.modules,
        "docx",
        type("docx", (), {"Document": FakeDocument}),
    )

    source = tmp_path / "doc.docx"
    source.write_bytes(b"PK placeholder")
    assert extract_text(str(source)) == "Heading\nBody paragraph."


def test_extract_text_accepts_bytes_data_for_txt(tmp_path: Path) -> None:
    source = tmp_path / "note.txt"
    source.write_text("Hello from data.", encoding="utf-8")
    assert extract_text(str(source), data=b"Hello from data.") == "Hello from data."


# --- normalization / checksum helpers -----------------------------------


def test_checksum_is_stable_across_line_endings() -> None:
    unix = "line one\nline two\n"
    windows = "line one\r\nline two\r\n"
    assert checksum_sha256(unix) == checksum_sha256(windows)


def test_normalize_text_collapses_crlf() -> None:
    assert normalize_text("a\r\nb\r\n") == "a\nb\n"
    assert normalize_text("a\rb") == "a\nb"


def test_document_chunk_model_contract() -> None:
    chunk = DocumentChunk(
        chunk_id="id",
        title="T",
        category="faq",
        version="1",
        chunk_text="x",
        token_count=1,
        character_count=1,
        checksum_sha256="a" * 64,
    )
    assert chunk.chunk_index == 0
    assert chunk.document_id is None
    assert chunk.heading is None
    assert chunk.page_number is None


def test_error_hierarchy_is_typed() -> None:
    assert issubclass(UnsupportedFileTypeError, IngestionError)
    assert issubclass(EmptyDocumentError, IngestionError)
    assert issubclass(MalformedDocumentError, IngestionError)
    assert issubclass(InvalidMetadataError, IngestionError)
    assert issubclass(DuplicateSourceError, IngestionError)
    assert issubclass(DocumentParseError, IngestionError)

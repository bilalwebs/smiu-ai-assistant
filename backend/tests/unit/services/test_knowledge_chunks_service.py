"""``knowledge_chunks`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import KnowledgeCategory
from app.services import KnowledgeChunkService
from app.services.exceptions import ConflictError, NotFoundError, ValidationError

_SHA256 = "c" * 64


async def _make_doc(knowledge_document_service, title: str = "Guide") -> object:
    return await knowledge_document_service.create_document(
        title=title,
        category=KnowledgeCategory.EXAMINATION,
        source_path=f"examination/{uuid.uuid4().hex}.pdf",
        checksum_sha256=_SHA256,
    )


async def test_create_chunk_happy_path(
    knowledge_document_service, knowledge_chunk_service
) -> None:
    doc = await _make_doc(knowledge_document_service)
    chunk = await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=0, chunk_text="Retrievable text"
    )
    assert chunk.knowledge_document_id == doc.id
    assert chunk.chunk_index == 0
    assert chunk.chunk_text == "Retrievable text"


async def test_create_chunk_updates_document_count(
    knowledge_document_service, knowledge_chunk_service
) -> None:
    doc = await _make_doc(knowledge_document_service)
    await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=0, chunk_text="A"
    )
    await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=1, chunk_text="B"
    )
    updated = await knowledge_document_service.get_document(document_id=doc.id)
    assert updated.chunk_count == 2


async def test_create_chunk_missing_document_raises(
    knowledge_chunk_service: KnowledgeChunkService,
) -> None:
    with pytest.raises(NotFoundError):
        await knowledge_chunk_service.create_chunk(
            knowledge_document_id=uuid.uuid4(), chunk_index=0, chunk_text="A"
        )


async def test_create_chunk_duplicate_index_raises(
    knowledge_document_service, knowledge_chunk_service
) -> None:
    doc = await _make_doc(knowledge_document_service)
    await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=0, chunk_text="A"
    )
    with pytest.raises(ConflictError):
        await knowledge_chunk_service.create_chunk(
            knowledge_document_id=doc.id, chunk_index=0, chunk_text="B"
        )


async def test_create_chunk_blank_text_raises(
    knowledge_document_service, knowledge_chunk_service
) -> None:
    doc = await _make_doc(knowledge_document_service)
    with pytest.raises(ValidationError):
        await knowledge_chunk_service.create_chunk(
            knowledge_document_id=doc.id, chunk_index=0, chunk_text="  "
        )


async def test_create_chunk_negative_index_raises(
    knowledge_document_service, knowledge_chunk_service
) -> None:
    doc = await _make_doc(knowledge_document_service)
    with pytest.raises(ValidationError):
        await knowledge_chunk_service.create_chunk(
            knowledge_document_id=doc.id, chunk_index=-1, chunk_text="A"
        )


async def test_create_chunk_negative_token_count_raises(
    knowledge_document_service, knowledge_chunk_service
) -> None:
    doc = await _make_doc(knowledge_document_service)
    with pytest.raises(ValidationError):
        await knowledge_chunk_service.create_chunk(
            knowledge_document_id=doc.id,
            chunk_index=0,
            chunk_text="A",
            token_count=-5,
        )


async def test_update_chunk_changes_heading(
    knowledge_document_service, knowledge_chunk_service
) -> None:
    doc = await _make_doc(knowledge_document_service)
    chunk = await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=0, chunk_text="A"
    )
    updated = await knowledge_chunk_service.update_chunk(
        chunk_id=chunk.id, heading="Admission rules"
    )
    assert updated.heading == "Admission rules"


async def test_update_chunk_to_existing_index_raises(
    knowledge_document_service, knowledge_chunk_service
) -> None:
    doc = await _make_doc(knowledge_document_service)
    first = await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=0, chunk_text="A"
    )
    await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=1, chunk_text="B"
    )
    with pytest.raises(ConflictError):
        await knowledge_chunk_service.update_chunk(
            chunk_id=first.id, chunk_index=1
        )


async def test_list_chunks_returns_index_order(
    knowledge_document_service, knowledge_chunk_service
) -> None:
    doc = await _make_doc(knowledge_document_service)
    first = await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=0, chunk_text="A"
    )
    second = await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=1, chunk_text="B"
    )
    chunks = await knowledge_chunk_service.list_chunks(knowledge_document_id=doc.id)
    assert [chunk.id for chunk in chunks] == [first.id, second.id]


async def test_list_chunks_missing_document_raises(
    knowledge_chunk_service: KnowledgeChunkService,
) -> None:
    with pytest.raises(NotFoundError):
        await knowledge_chunk_service.list_chunks(knowledge_document_id=uuid.uuid4())

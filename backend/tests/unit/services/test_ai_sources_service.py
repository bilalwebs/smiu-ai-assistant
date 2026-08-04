"""``ai_sources`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import KnowledgeCategory, MessageRole, SourceType
from app.services import AISourceService
from app.services.exceptions import ConflictError, NotFoundError, ValidationError

_SHA256 = "d" * 64


async def _message_and_chunk(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    user_factory,
):
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    message = await chat_history_service.add_message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content="Your admission requires your transcript.",
    )
    doc = await knowledge_document_service.create_document(
        title="Guide",
        category=KnowledgeCategory.ADMISSION,
        source_path=f"admission/{uuid.uuid4().hex}.pdf",
        checksum_sha256=_SHA256,
    )
    chunk = await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id, chunk_index=0, chunk_text="Transcript required"
    )
    return message, doc, chunk


async def test_create_source_happy_path(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, chunk = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    source = await ai_source_service.create_source(
        message_id=message.id,
        source_title="BSSE Admission Guide",
        knowledge_document_id=doc.id,
        knowledge_chunk_id=chunk.id,
    )
    assert source.message_id == message.id
    assert source.source_title == "BSSE Admission Guide"
    assert source.source_type == SourceType.RAG
    assert source.knowledge_chunk_id == chunk.id


async def test_create_source_without_chunk(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, _ = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    source = await ai_source_service.create_source(
        message_id=message.id,
        source_title="Manual note",
        source_type=SourceType.MANUAL,
        knowledge_document_id=doc.id,
        source_url="https://smiu.edu.pk/admissions",
    )
    assert source.source_type == SourceType.MANUAL
    assert source.knowledge_chunk_id is None


async def test_create_source_blank_title_raises(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, chunk = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    with pytest.raises(ValidationError):
        await ai_source_service.create_source(
            message_id=message.id,
            source_title="  ",
            knowledge_document_id=doc.id,
            knowledge_chunk_id=chunk.id,
        )


async def test_create_source_invalid_type_raises(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, chunk = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    with pytest.raises(ValidationError):
        await ai_source_service.create_source(
            message_id=message.id,
            source_title="Guide",
            source_type="bogus",
            knowledge_document_id=doc.id,
            knowledge_chunk_id=chunk.id,
        )


async def test_create_source_relevance_out_of_range_raises(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, chunk = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    with pytest.raises(ValidationError):
        await ai_source_service.create_source(
            message_id=message.id,
            source_title="Guide",
            relevance_score=1.5,
            knowledge_document_id=doc.id,
            knowledge_chunk_id=chunk.id,
        )


async def test_create_source_missing_message_raises(
    ai_source_service: AISourceService,
) -> None:
    with pytest.raises(NotFoundError):
        await ai_source_service.create_source(
            message_id=uuid.uuid4(), source_title="Guide"
        )


async def test_create_source_missing_document_raises(
    conversation_service,
    chat_history_service,
    ai_source_service,
    user_factory,
) -> None:
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    message = await chat_history_service.add_message(
        conversation_id=conversation.id, role=MessageRole.ASSISTANT, content="Hi"
    )
    with pytest.raises(NotFoundError):
        await ai_source_service.create_source(
            message_id=message.id,
            source_title="Guide",
            knowledge_document_id=uuid.uuid4(),
        )


async def test_create_source_missing_chunk_raises(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, _ = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    with pytest.raises(NotFoundError):
        await ai_source_service.create_source(
            message_id=message.id,
            source_title="Guide",
            knowledge_document_id=doc.id,
            knowledge_chunk_id=uuid.uuid4(),
        )


async def test_create_source_duplicate_chunk_raises(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, chunk = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    await ai_source_service.create_source(
        message_id=message.id,
        source_title="Guide",
        knowledge_document_id=doc.id,
        knowledge_chunk_id=chunk.id,
    )
    with pytest.raises(ConflictError):
        await ai_source_service.create_source(
            message_id=message.id,
            source_title="Guide again",
            knowledge_document_id=doc.id,
            knowledge_chunk_id=chunk.id,
        )


async def test_update_source_changes_snapshot(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, chunk = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    source = await ai_source_service.create_source(
        message_id=message.id,
        source_title="Guide",
        knowledge_document_id=doc.id,
        knowledge_chunk_id=chunk.id,
    )
    updated = await ai_source_service.update_source(
        source_id=source.id, source_title="Guide v2", snippet="New snippet"
    )
    assert updated.source_title == "Guide v2"
    assert updated.snippet == "New snippet"


async def test_update_source_invalid_relevance_raises(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, chunk = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    source = await ai_source_service.create_source(
        message_id=message.id,
        source_title="Guide",
        knowledge_document_id=doc.id,
        knowledge_chunk_id=chunk.id,
    )
    with pytest.raises(ValidationError):
        await ai_source_service.update_source(
            source_id=source.id, relevance_score=-0.1
        )


async def test_update_source_missing_raises(
    ai_source_service: AISourceService,
) -> None:
    with pytest.raises(NotFoundError):
        await ai_source_service.update_source(source_id=uuid.uuid4(), source_title="X")


async def test_list_sources_returns_retrieval_order(
    conversation_service,
    chat_history_service,
    knowledge_document_service,
    knowledge_chunk_service,
    ai_source_service,
    user_factory,
) -> None:
    message, doc, chunk = await _message_and_chunk(
        conversation_service,
        chat_history_service,
        knowledge_document_service,
        knowledge_chunk_service,
        user_factory,
    )
    first = await ai_source_service.create_source(
        message_id=message.id,
        source_title="First",
        knowledge_document_id=doc.id,
        knowledge_chunk_id=chunk.id,
    )
    second = await ai_source_service.create_source(
        message_id=message.id, source_title="Second"
    )
    sources = await ai_source_service.list_sources(message_id=message.id)
    assert [source.id for source in sources] == [first.id, second.id]


async def test_list_sources_missing_message_raises(
    ai_source_service: AISourceService,
) -> None:
    with pytest.raises(NotFoundError):
        await ai_source_service.list_sources(message_id=uuid.uuid4())

"""``knowledge_documents`` / ``knowledge_chunks`` / ``ai_sources`` repository helpers
(DATABASE_DESIGN.md §21, §22)."""

from __future__ import annotations

from datetime import timedelta

from app.models import KnowledgeCategory
from app.repositories import (
    AISourceRepository,
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)
from app.utils.time import utc_now


async def test_search_by_category_filters_and_sorts(
    db_session, knowledge_document_factory
) -> None:
    a = await knowledge_document_factory(category=KnowledgeCategory.ADMISSION, title="Zed")
    b = await knowledge_document_factory(
        category=KnowledgeCategory.ADMISSION, title="Alpha"
    )
    await knowledge_document_factory(
        category=KnowledgeCategory.ADMISSION, title="Mid", is_active=False
    )
    await knowledge_document_factory(category=KnowledgeCategory.EXAMINATION, title="Other")
    repo = KnowledgeDocumentRepository(db_session)
    rows = await repo.search_by_category(KnowledgeCategory.ADMISSION)
    assert [row.id for row in rows] == [b.id, a.id]


async def test_search_by_category_excludes_soft_deleted(
    db_session, knowledge_document_factory
) -> None:
    live = await knowledge_document_factory(category=KnowledgeCategory.ADMISSION)
    gone = await knowledge_document_factory(category=KnowledgeCategory.ADMISSION)
    repo = KnowledgeDocumentRepository(db_session)
    await repo.soft_delete(gone)
    rows = await repo.search_by_category(KnowledgeCategory.ADMISSION)
    assert [row.id for row in rows] == [live.id]


async def test_get_active_documents_newest_first(db_session, knowledge_document_factory) -> None:
    now = utc_now()
    d1 = await knowledge_document_factory(created_at=now)
    d2 = await knowledge_document_factory(
        created_at=now - timedelta(minutes=1)
    )
    await knowledge_document_factory(
        is_active=False, created_at=now - timedelta(minutes=2)
    )
    repo = KnowledgeDocumentRepository(db_session)
    rows = await repo.get_active_documents()
    assert [row.id for row in rows] == [d1.id, d2.id]


async def test_chunks_listed_in_index_order(
    db_session, knowledge_document_factory, knowledge_chunk_factory
) -> None:
    doc = await knowledge_document_factory()
    other_doc = await knowledge_document_factory()
    c0 = await knowledge_chunk_factory(knowledge_document_id=doc.id, chunk_index=0)
    c1 = await knowledge_chunk_factory(knowledge_document_id=doc.id, chunk_index=1)
    await knowledge_chunk_factory(knowledge_document_id=other_doc.id, chunk_index=0)
    repo = KnowledgeChunkRepository(db_session)
    rows = await repo.list_by_document(doc.id)
    assert [row.id for row in rows] == [c0.id, c1.id]


async def test_ai_sources_listed_in_retrieval_order(
    db_session, user_factory, conversation_factory, message_factory, ai_source_factory
) -> None:
    conv = await conversation_factory(user_id=(await user_factory()).id)
    msg = await message_factory(conversation_id=conv.id)
    other_msg = await message_factory(conversation_id=conv.id)
    now = utc_now()
    s1 = await ai_source_factory(message_id=msg.id, source_title="first", retrieved_at=now)
    s2 = await ai_source_factory(
        message_id=msg.id, source_title="second", retrieved_at=now - timedelta(minutes=1)
    )
    await ai_source_factory(message_id=other_msg.id)
    repo = AISourceRepository(db_session)
    rows = await repo.list_by_message(msg.id)
    assert [row.id for row in rows] == [s2.id, s1.id]

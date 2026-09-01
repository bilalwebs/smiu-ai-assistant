"""``ai_chat`` user document context tests.

Tests ``_link_documents_to_message`` and ``_load_user_document_texts`` on the
AIChatService without requiring a compiled workflow (avoids ``ai`` module
import dependency).
"""

from __future__ import annotations

import uuid
from typing import Any, Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentCategory, DocumentStatus, User
from app.repositories import DocumentRepository
from app.services import AIChatService, UserService


@pytest.fixture()
def user_svc(db_session: AsyncSession) -> UserService:
    return UserService(db_session)


@pytest.fixture()
def doc_repo(db_session: AsyncSession) -> DocumentRepository:
    return DocumentRepository(db_session)


@pytest.fixture()
def user_factory(
    user_svc: UserService,
) -> Callable[..., Awaitable[User]]:
    async def _make(**overrides: Any) -> User:
        values: dict[str, Any] = {
            "email": f"{uuid.uuid4().hex}@example.com",
            "password_hash": "hashed",
            "full_name": "Doc Test User",
        }
        values.update(overrides)
        return await user_svc.create_user(**values)
    return _make


@pytest.fixture()
def doc_factory(
    db_session: AsyncSession,
) -> Callable[..., Awaitable[Document]]:
    repo = DocumentRepository(db_session)

    async def _make(
        *, user_id: uuid.UUID, **overrides: Any
    ) -> Document:
        suffix = uuid.uuid4().hex[:8]
        values: dict[str, Any] = {
            "user_id": user_id,
            "original_filename": f"file-{suffix}.pdf",
            "stored_filename": f"stored-{suffix}.pdf",
            "file_path": f"uploads/{suffix}.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
            "checksum_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
        }
        values.update(overrides)
        return await repo.create(**values)
    return _make


@pytest.fixture()
def chat_svc(db_session: AsyncSession) -> AIChatService:
    """AIChatService without a workflow — only document methods are exercised."""
    return AIChatService(db_session, workflow=None)


# -- _link_documents_to_message tests -----------------------------------------


async def test_link_documents_sets_message_id(
    chat_svc: AIChatService,
    doc_factory: Callable[..., Awaitable[Document]],
    user_factory: Callable[..., Awaitable[User]],
) -> None:
    user = await user_factory()
    doc = await doc_factory(user_id=user.id)
    msg_id = uuid.uuid4()

    await chat_svc._link_documents_to_message(
        user_id=user.id, document_ids=[doc.id], message_id=msg_id,
    )
    await chat_svc._session.flush()

    refreshed = await chat_svc._session.get(Document, doc.id)
    assert refreshed.message_id == msg_id


async def test_link_documents_skips_other_users(
    chat_svc: AIChatService,
    doc_factory: Callable[..., Awaitable[Document]],
    user_factory: Callable[..., Awaitable[User]],
) -> None:
    user_a = await user_factory()
    user_b = await user_factory()
    other_doc = await doc_factory(user_id=user_b.id)
    msg_id = uuid.uuid4()

    await chat_svc._link_documents_to_message(
        user_id=user_a.id, document_ids=[other_doc.id], message_id=msg_id,
    )
    await chat_svc._session.flush()

    refreshed = await chat_svc._session.get(Document, other_doc.id)
    assert refreshed.message_id is None


async def test_link_documents_skips_nonexistent(
    chat_svc: AIChatService,
    user_factory: Callable[..., Awaitable[User]],
) -> None:
    user = await user_factory()
    fake_id = uuid.uuid4()

    # Should not raise
    await chat_svc._link_documents_to_message(
        user_id=user.id, document_ids=[fake_id], message_id=uuid.uuid4(),
    )
    await chat_svc._session.flush()


async def test_link_documents_empty_list_is_noop(
    chat_svc: AIChatService,
    user_factory: Callable[..., Awaitable[User]],
) -> None:
    user = await user_factory()
    # Should not raise
    await chat_svc._link_documents_to_message(
        user_id=user.id, document_ids=[], message_id=uuid.uuid4(),
    )


# -- _load_user_document_texts tests ------------------------------------------


async def test_load_texts_returns_extracted_content(
    chat_svc: AIChatService,
    doc_factory: Callable[..., Awaitable[Document]],
    user_factory: Callable[..., Awaitable[User]],
    tmp_path,
) -> None:
    user = await user_factory()
    doc = await doc_factory(
        user_id=user.id,
        status=DocumentStatus.PROCESSED,
    )
    text_file = tmp_path / "extracted.txt"
    text_file.write_text("Student Name: Alice\nApp ID: APP-123")
    doc.extracted_text_path = str(text_file)
    await chat_svc._session.flush()

    texts = await chat_svc._load_user_document_texts(
        user_id=user.id, document_ids=[doc.id],
    )
    assert texts == ["Student Name: Alice\nApp ID: APP-123"]


async def test_load_texts_skips_other_users(
    chat_svc: AIChatService,
    doc_factory: Callable[..., Awaitable[Document]],
    user_factory: Callable[..., Awaitable[User]],
    tmp_path,
) -> None:
    user_a = await user_factory()
    user_b = await user_factory()
    doc_b = await doc_factory(user_id=user_b.id, status=DocumentStatus.PROCESSED)
    text_file = tmp_path / "secret.txt"
    text_file.write_text("SECRET DATA")
    doc_b.extracted_text_path = str(text_file)
    await chat_svc._session.flush()

    texts = await chat_svc._load_user_document_texts(
        user_id=user_a.id, document_ids=[doc_b.id],
    )
    assert texts == []


async def test_load_texts_skips_no_text_path(
    chat_svc: AIChatService,
    doc_factory: Callable[..., Awaitable[Document]],
    user_factory: Callable[..., Awaitable[User]],
) -> None:
    user = await user_factory()
    doc = await doc_factory(user_id=user.id)
    # extracted_text_path is None by default
    await chat_svc._session.flush()

    texts = await chat_svc._load_user_document_texts(
        user_id=user.id, document_ids=[doc.id],
    )
    assert texts == []


async def test_load_texts_skips_nonexistent(
    chat_svc: AIChatService,
    user_factory: Callable[..., Awaitable[User]],
) -> None:
    user = await user_factory()
    texts = await chat_svc._load_user_document_texts(
        user_id=user.id, document_ids=[uuid.uuid4()],
    )
    assert texts == []


async def test_load_texts_empty_list(
    chat_svc: AIChatService,
    user_factory: Callable[..., Awaitable[User]],
) -> None:
    user = await user_factory()
    texts = await chat_svc._load_user_document_texts(
        user_id=user.id, document_ids=[],
    )
    assert texts == []


async def test_load_texts_multiple_docs(
    chat_svc: AIChatService,
    doc_factory: Callable[..., Awaitable[Document]],
    user_factory: Callable[..., Awaitable[User]],
    tmp_path,
) -> None:
    user = await user_factory()
    doc1 = await doc_factory(user_id=user.id, status=DocumentStatus.PROCESSED)
    doc2 = await doc_factory(user_id=user.id, status=DocumentStatus.PROCESSED)

    f1 = tmp_path / "d1.txt"
    f1.write_text("First document")
    doc1.extracted_text_path = str(f1)

    f2 = tmp_path / "d2.txt"
    f2.write_text("Second document")
    doc2.extracted_text_path = str(f2)
    await chat_svc._session.flush()

    texts = await chat_svc._load_user_document_texts(
        user_id=user.id, document_ids=[doc1.id, doc2.id],
    )
    assert texts == ["First document", "Second document"]

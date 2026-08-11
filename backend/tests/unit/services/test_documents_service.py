"""``documents`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import DocumentCategory, DocumentStatus
from app.services import DocumentService
from app.services.exceptions import BusinessRuleError, NotFoundError, ValidationError

_SHA256 = "a" * 64


def _doc_kwargs(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "user_id": uuid.uuid4(),
        "original_filename": "transcript.pdf",
        "stored_filename": "stored-transcript.pdf",
        "file_path": "uploads/stored-transcript.pdf",
        "size_bytes": 2048,
        "checksum_sha256": _SHA256,
    }
    values.update(overrides)
    return values


async def test_create_document_happy_path(document_service, user_factory) -> None:
    user = await user_factory()
    doc = await document_service.create_document(
        user_id=user.id,
        original_filename="transcript.pdf",
        stored_filename="stored-transcript.pdf",
        file_path="uploads/stored-transcript.pdf",
        size_bytes=2048,
        checksum_sha256=_SHA256,
    )
    assert doc.user_id == user.id
    assert doc.category == DocumentCategory.OTHER
    assert doc.status == DocumentStatus.PENDING
    assert doc.size_bytes == 2048


async def test_create_document_explicit_category(
    document_service, user_factory
) -> None:
    user = await user_factory()
    doc = await document_service.create_document(
        **_doc_kwargs(user_id=user.id, category=DocumentCategory.IDENTITY)
    )
    assert doc.category == DocumentCategory.IDENTITY


async def test_create_document_without_owner_raises(
    document_service: DocumentService,
) -> None:
    kwargs = _doc_kwargs()
    kwargs.pop("user_id")
    with pytest.raises(BusinessRuleError):
        await document_service.create_document(**kwargs)


async def test_create_document_missing_user_raises(
    document_service: DocumentService,
) -> None:
    with pytest.raises(NotFoundError):
        await document_service.create_document(**_doc_kwargs())


async def test_create_document_invalid_checksum_raises(
    document_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await document_service.create_document(
            **_doc_kwargs(user_id=user.id, checksum_sha256="short")
        )


async def test_create_document_non_positive_size_raises(
    document_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await document_service.create_document(
            **_doc_kwargs(user_id=user.id, size_bytes=0)
        )


async def test_create_document_blank_filename_raises(
    document_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await document_service.create_document(
            **_doc_kwargs(user_id=user.id, original_filename="  ")
        )


async def test_update_document_renames(document_service, user_factory) -> None:
    user = await user_factory()
    doc = await document_service.create_document(**_doc_kwargs(user_id=user.id))
    updated = await document_service.update_document(
        document_id=doc.id, original_filename="renamed.pdf"
    )
    assert updated.original_filename == "renamed.pdf"


async def test_update_document_removing_all_owners_raises(
    document_service, user_factory
) -> None:
    user = await user_factory()
    doc = await document_service.create_document(**_doc_kwargs(user_id=user.id))
    with pytest.raises(BusinessRuleError):
        await document_service.update_document(
            document_id=doc.id,
            user_id=None,
            request_id=None,
            message_id=None,
        )


async def test_update_document_invalid_size_raises(
    document_service, user_factory
) -> None:
    user = await user_factory()
    doc = await document_service.create_document(**_doc_kwargs(user_id=user.id))
    with pytest.raises(ValidationError):
        await document_service.update_document(document_id=doc.id, size_bytes=-1)


async def test_update_document_missing_raises(
    document_service: DocumentService,
) -> None:
    with pytest.raises(NotFoundError):
        await document_service.update_document(
            document_id=uuid.uuid4(), original_filename="x.pdf"
        )


async def test_archive_and_restore_document(document_service, user_factory) -> None:
    user = await user_factory()
    doc = await document_service.create_document(**_doc_kwargs(user_id=user.id))
    archived = await document_service.archive_document(document_id=doc.id)
    assert archived.is_deleted
    restored = await document_service.restore_document(document_id=doc.id)
    assert not restored.is_deleted


async def test_restore_missing_document_raises(
    document_service: DocumentService,
) -> None:
    with pytest.raises(NotFoundError):
        await document_service.restore_document(document_id=uuid.uuid4())

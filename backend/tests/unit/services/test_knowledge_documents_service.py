"""``knowledge_documents`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import KnowledgeCategory, KnowledgeStatus
from app.services import KnowledgeDocumentService
from app.services.exceptions import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)

_SHA256 = "b" * 64


async def test_create_document_happy_path(knowledge_document_service) -> None:
    doc = await knowledge_document_service.create_document(
        title="BSSE Admission Guide",
        category=KnowledgeCategory.ADMISSION,
        source_path="admission/bsse-guide.pdf",
        checksum_sha256=_SHA256,
    )
    assert doc.title == "BSSE Admission Guide"
    assert doc.category == KnowledgeCategory.ADMISSION
    assert doc.status == KnowledgeStatus.PENDING
    assert doc.is_active is True
    assert doc.version == "1"


async def test_create_document_duplicate_source_version_raises(
    knowledge_document_service,
) -> None:
    await knowledge_document_service.create_document(
        title="Guide",
        category=KnowledgeCategory.FAQ,
        source_path="faq/guide.md",
        checksum_sha256=_SHA256,
    )
    with pytest.raises(ConflictError):
        await knowledge_document_service.create_document(
            title="Guide again",
            category=KnowledgeCategory.FAQ,
            source_path="faq/guide.md",
            checksum_sha256=_SHA256,
        )


async def test_create_document_new_version_allowed(
    knowledge_document_service,
) -> None:
    await knowledge_document_service.create_document(
        title="Guide v1",
        category=KnowledgeCategory.FAQ,
        source_path="faq/guide.md",
        checksum_sha256=_SHA256,
        version="1",
    )
    doc = await knowledge_document_service.create_document(
        title="Guide v2",
        category=KnowledgeCategory.FAQ,
        source_path="faq/guide.md",
        checksum_sha256=_SHA256,
        version="2",
    )
    assert doc.version == "2"


async def test_create_document_blank_title_raises(
    knowledge_document_service: KnowledgeDocumentService,
) -> None:
    with pytest.raises(ValidationError):
        await knowledge_document_service.create_document(
            title="  ",
            category=KnowledgeCategory.FAQ,
            source_path="faq/x.md",
            checksum_sha256=_SHA256,
        )


async def test_create_document_invalid_checksum_raises(
    knowledge_document_service: KnowledgeDocumentService,
) -> None:
    with pytest.raises(InvalidStateError):
        await knowledge_document_service.create_document(
            title="Guide",
            category=KnowledgeCategory.FAQ,
            source_path="faq/x.md",
            checksum_sha256="xyz",
        )


async def test_create_document_non_positive_file_size_raises(
    knowledge_document_service: KnowledgeDocumentService,
) -> None:
    with pytest.raises(InvalidStateError):
        await knowledge_document_service.create_document(
            title="Guide",
            category=KnowledgeCategory.FAQ,
            source_path="faq/x.md",
            checksum_sha256=_SHA256,
            file_size=0,
        )


async def test_publish_document(knowledge_document_service) -> None:
    doc = await knowledge_document_service.create_document(
        title="Guide",
        category=KnowledgeCategory.ADMISSION,
        source_path="admission/guide.pdf",
        checksum_sha256=_SHA256,
    )
    published = await knowledge_document_service.publish_document(document_id=doc.id)
    assert published.status == KnowledgeStatus.PROCESSED
    assert published.is_active is True
    assert published.indexed_at is not None


async def test_publish_processed_document_raises(knowledge_document_service) -> None:
    doc = await knowledge_document_service.create_document(
        title="Guide",
        category=KnowledgeCategory.ADMISSION,
        source_path="admission/guide.pdf",
        checksum_sha256=_SHA256,
    )
    await knowledge_document_service.publish_document(document_id=doc.id)
    with pytest.raises(InvalidStateError):
        await knowledge_document_service.publish_document(document_id=doc.id)


async def test_archive_document_removes_from_retrieval(
    knowledge_document_service,
) -> None:
    doc = await knowledge_document_service.create_document(
        title="Guide",
        category=KnowledgeCategory.ADMISSION,
        source_path="admission/guide.pdf",
        checksum_sha256=_SHA256,
    )
    await knowledge_document_service.publish_document(document_id=doc.id)
    archived = await knowledge_document_service.archive_document(document_id=doc.id)
    assert archived.status == KnowledgeStatus.ARCHIVED
    assert archived.is_active is False


async def test_archive_archived_document_raises(knowledge_document_service) -> None:
    doc = await knowledge_document_service.create_document(
        title="Guide",
        category=KnowledgeCategory.ADMISSION,
        source_path="admission/guide.pdf",
        checksum_sha256=_SHA256,
    )
    await knowledge_document_service.archive_document(document_id=doc.id)
    with pytest.raises(InvalidStateError):
        await knowledge_document_service.archive_document(document_id=doc.id)


async def test_change_status_rejects_backward_transition(
    knowledge_document_service,
) -> None:
    doc = await knowledge_document_service.create_document(
        title="Guide",
        category=KnowledgeCategory.ADMISSION,
        source_path="admission/guide.pdf",
        checksum_sha256=_SHA256,
    )
    processing = await knowledge_document_service.change_status(
        document_id=doc.id, status=KnowledgeStatus.PROCESSING
    )
    assert processing.status == KnowledgeStatus.PROCESSING
    with pytest.raises(InvalidStateError):
        await knowledge_document_service.change_status(
            document_id=doc.id, status=KnowledgeStatus.PENDING
        )


async def test_change_status_same_status_raises(knowledge_document_service) -> None:
    doc = await knowledge_document_service.create_document(
        title="Guide",
        category=KnowledgeCategory.ADMISSION,
        source_path="admission/guide.pdf",
        checksum_sha256=_SHA256,
    )
    with pytest.raises(InvalidStateError):
        await knowledge_document_service.change_status(
            document_id=doc.id, status=KnowledgeStatus.PENDING
        )


async def test_missing_document_raises(
    knowledge_document_service: KnowledgeDocumentService,
) -> None:
    with pytest.raises(NotFoundError):
        await knowledge_document_service.get_document(document_id=uuid.uuid4())

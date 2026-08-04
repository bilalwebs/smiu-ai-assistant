"""``knowledge_documents`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §21.1).

AI & Knowledge: source metadata for indexed RAG documents. The service owns the
ingestion lifecycle (pending → processing → processed/failed → archived) and the
``is_active`` retrieval flag; only ``is_active`` + ``processed`` documents
participate in retrieval (DATABASE_DESIGN.md §21.3).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeCategory, KnowledgeDocument, KnowledgeStatus
from app.repositories import KnowledgeDocumentRepository, Page
from app.services.base import BaseService
from app.services.exceptions import ConflictError, InvalidStateError, NotFoundError
from app.utils.time import utc_now

_ALLOWED_TRANSITIONS: dict[KnowledgeStatus, frozenset[KnowledgeStatus]] = {
    KnowledgeStatus.PENDING: frozenset(
        {
            KnowledgeStatus.PROCESSING,
            KnowledgeStatus.PROCESSED,
            KnowledgeStatus.FAILED,
            KnowledgeStatus.ARCHIVED,
        }
    ),
    KnowledgeStatus.PROCESSING: frozenset(
        {
            KnowledgeStatus.PROCESSED,
            KnowledgeStatus.FAILED,
            KnowledgeStatus.ARCHIVED,
        }
    ),
    KnowledgeStatus.PROCESSED: frozenset(
        {KnowledgeStatus.PROCESSING, KnowledgeStatus.ARCHIVED}
    ),
    KnowledgeStatus.FAILED: frozenset(
        {
            KnowledgeStatus.PROCESSING,
            KnowledgeStatus.PROCESSED,
            KnowledgeStatus.ARCHIVED,
        }
    ),
    KnowledgeStatus.ARCHIVED: frozenset(),
}


class KnowledgeDocumentService(BaseService):
    """Knowledge source operations for
    :class:`app.models.knowledge_documents.KnowledgeDocument`.
    """

    def __init__(
        self,
        session: AsyncSession,
        documents: KnowledgeDocumentRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._documents = documents or KnowledgeDocumentRepository(session)

    async def create_document(
        self,
        *,
        title: str,
        category: KnowledgeCategory,
        source_path: str,
        checksum_sha256: str,
        file_type: str | None = None,
        file_size: int | None = None,
        author: str | None = None,
        version: str = "1",
        status: KnowledgeStatus = KnowledgeStatus.PENDING,
        is_active: bool = True,
        metadata_: dict[str, Any] | None = None,
    ) -> KnowledgeDocument:
        """Register a knowledge source after shape and uniqueness validation."""
        title = self._validate_not_blank(title, field="title")
        category = self._validate_enum(category, KnowledgeCategory, field="category")
        source_path = self._validate_not_blank(source_path, field="source_path")
        checksum_sha256 = self._validate_checksum(checksum_sha256, field="checksum_sha256")
        version = self._validate_not_blank(version, field="version")
        if len(version) > 30:
            raise InvalidStateError(
                message="version must be at most 30 characters",
                details=[{"field": "version", "reason": "too long"}],
            )
        if file_size is not None and file_size <= 0:
            raise InvalidStateError(
                message="file_size must be positive",
                details=[{"field": "file_size", "reason": "must be positive"}],
            )
        status = self._validate_enum(status, KnowledgeStatus, field="status")
        existing = await self._documents.get(
            KnowledgeDocument.source_path == source_path,
            KnowledgeDocument.version == version,
        )
        if existing is not None:
            raise ConflictError(
                message="A document with this source path and version already exists",
                details=[
                    {"field": "source_path", "reason": "already in use"},
                    {"field": "version", "reason": "already in use"},
                ],
            )
        values: dict[str, Any] = {
            "title": title,
            "category": category,
            "source_path": source_path,
            "file_type": file_type,
            "file_size": file_size,
            "author": author,
            "version": version,
            "checksum_sha256": checksum_sha256,
            "status": status,
            "is_active": is_active,
        }
        if metadata_ is not None:
            values["metadata_"] = metadata_
        return await self._documents.create(**values)

    async def update_document(
        self, *, document_id: uuid.UUID, **changes: Any
    ) -> KnowledgeDocument:
        """Update knowledge source metadata with per-field validation."""
        document = await self._require_document(document_id)
        if "title" in changes:
            changes["title"] = self._validate_not_blank(changes["title"], field="title")
        if "category" in changes:
            changes["category"] = self._validate_enum(
                changes["category"], KnowledgeCategory, field="category"
            )
        if "source_path" in changes:
            changes["source_path"] = self._validate_not_blank(
                changes["source_path"], field="source_path"
            )
        if "checksum_sha256" in changes:
            changes["checksum_sha256"] = self._validate_checksum(
                changes["checksum_sha256"], field="checksum_sha256"
            )
        if "version" in changes:
            changes["version"] = self._validate_not_blank(
                changes["version"], field="version"
            )
        if (
            "file_size" in changes
            and changes["file_size"] is not None
            and changes["file_size"] <= 0
        ):
            raise InvalidStateError(
                    message="file_size must be positive",
                    details=[{"field": "file_size", "reason": "must be positive"}],
                )
        if "status" in changes:
            changes["status"] = self._validate_enum(
                changes["status"], KnowledgeStatus, field="status"
            )
        source_path = changes.get("source_path", document.source_path)
        version = changes.get("version", document.version)
        if source_path != document.source_path or version != document.version:
            existing = await self._documents.get(
                KnowledgeDocument.source_path == source_path,
                KnowledgeDocument.version == version,
            )
            if existing is not None and existing.id != document.id:
                raise ConflictError(
                    message="A document with this source path and version already exists",
                    details=[
                        {"field": "source_path", "reason": "already in use"},
                        {"field": "version", "reason": "already in use"},
                    ],
                )
        return await self._documents.update(document, **changes)

    async def get_document(self, *, document_id: uuid.UUID) -> KnowledgeDocument:
        """Return a live knowledge document or raise 404."""
        return await self._require_document(document_id)

    async def list_documents(
        self, *, page: int = 1, limit: int = 20
    ) -> Page[KnowledgeDocument]:
        """Paginate all knowledge documents, newest first (admin-only, §25)."""
        return await self._documents.paginate(
            page=page,
            limit=limit,
            order_by=[KnowledgeDocument.created_at.desc()],
        )

    async def change_status(
        self, *, document_id: uuid.UUID, status: KnowledgeStatus
    ) -> KnowledgeDocument:
        """Transition a document through the ingestion state machine."""
        document = await self._require_document(document_id)
        status = self._validate_enum(status, KnowledgeStatus, field="status")
        if status == document.status:
            raise InvalidStateError(
                message=f"Document is already {document.status.value}",
                details=[{"field": "status", "reason": "no state change"}],
            )
        allowed = _ALLOWED_TRANSITIONS.get(document.status, frozenset())
        if status not in allowed:
            raise InvalidStateError(
                message=(
                    f"Cannot transition document from {document.status.value} "
                    f"to {status.value}"
                ),
                details=[{"field": "status", "reason": "invalid transition"}],
            )
        return await self._documents.update(document, status=status)

    async def publish_document(
        self, *, document_id: uuid.UUID
    ) -> KnowledgeDocument:
        """Mark a document processed and active (retrievable)."""
        document = await self._require_document(document_id)
        status = self._validate_enum(
            KnowledgeStatus.PROCESSED, KnowledgeStatus, field="status"
        )
        if status == document.status:
            raise InvalidStateError(message="Document is already processed")
        allowed = _ALLOWED_TRANSITIONS.get(document.status, frozenset())
        if status not in allowed:
            raise InvalidStateError(
                message=(
                    f"Cannot transition document from {document.status.value} "
                    f"to {status.value}"
                ),
                details=[{"field": "status", "reason": "invalid transition"}],
            )
        return await self._documents.update(
            document,
            status=KnowledgeStatus.PROCESSED,
            is_active=True,
            indexed_at=utc_now(),
        )

    async def archive_document(
        self, *, document_id: uuid.UUID
    ) -> KnowledgeDocument:
        """Archive a document, removing it from retrieval."""
        document = await self._require_document(document_id)
        allowed = _ALLOWED_TRANSITIONS.get(document.status, frozenset())
        if KnowledgeStatus.ARCHIVED not in allowed:
            raise InvalidStateError(
                message=(
                    f"Cannot transition document from {document.status.value} "
                    f"to {KnowledgeStatus.ARCHIVED.value}"
                ),
                details=[{"field": "status", "reason": "invalid transition"}],
            )
        return await self._documents.update(
            document,
            status=KnowledgeStatus.ARCHIVED,
            is_active=False,
        )

    @staticmethod
    def _validate_checksum(checksum_sha256: str, *, field: str) -> str:
        checksum_sha256 = KnowledgeDocumentService._validate_not_blank(
            checksum_sha256, field=field
        )
        if len(checksum_sha256) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in checksum_sha256
        ):
            raise InvalidStateError(
                message=f"{field} must be a 64-character SHA-256 hex digest",
                details=[{"field": field, "reason": "not a sha256 hex digest"}],
            )
        return checksum_sha256

    async def _require_document(
        self, document_id: uuid.UUID
    ) -> KnowledgeDocument:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise NotFoundError(message="Knowledge document not found")
        return document

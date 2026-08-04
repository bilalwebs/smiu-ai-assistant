"""``documents`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §20).

Workflow & Support: metadata for uploaded files. Only metadata is persisted —
file bytes live on the dedicated storage path. The service enforces the
owner-check (one of user/request/message) and size/checksum rules from the
schema constraints (DATABASE_DESIGN.md §20).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentCategory, DocumentStatus
from app.repositories import (
    ChatMessageRepository,
    DocumentRepository,
    RequestRepository,
    UserRepository,
)
from app.services.base import BaseService
from app.services.exceptions import BusinessRuleError, NotFoundError, ValidationError


class DocumentService(BaseService):
    """Document-metadata operations for :class:`app.models.documents.Document`."""

    def __init__(
        self,
        session: AsyncSession,
        documents: DocumentRepository | None = None,
        users: UserRepository | None = None,
        requests: RequestRepository | None = None,
        messages: ChatMessageRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._documents = documents or DocumentRepository(session)
        self._users = users or UserRepository(session)
        self._requests = requests or RequestRepository(session)
        self._messages = messages or ChatMessageRepository(session)

    async def create_document(
        self,
        *,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        size_bytes: int,
        checksum_sha256: str,
        user_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        message_id: uuid.UUID | None = None,
        category: DocumentCategory = DocumentCategory.OTHER,
        content_type: str | None = None,
        status: DocumentStatus = DocumentStatus.PENDING,
        extracted_text_path: str | None = None,
    ) -> Document:
        """Register uploaded-file metadata after owner and shape validation."""
        self._assert_owner(user_id, request_id, message_id)
        await self._validate_owners(user_id, request_id, message_id)
        original_filename = self._validate_not_blank(
            original_filename, field="original_filename"
        )
        stored_filename = self._validate_not_blank(
            stored_filename, field="stored_filename"
        )
        file_path = self._validate_not_blank(file_path, field="file_path")
        checksum_sha256 = self._validate_checksum(checksum_sha256, field="checksum_sha256")
        if size_bytes <= 0:
            raise ValidationError(
                message="size_bytes must be positive",
                details=[{"field": "size_bytes", "reason": "must be positive"}],
            )
        category = self._validate_enum(category, DocumentCategory, field="category")
        status = self._validate_enum(status, DocumentStatus, field="status")
        return await self._documents.create(
            user_id=user_id,
            request_id=request_id,
            message_id=message_id,
            category=category,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            status=status,
            extracted_text_path=extracted_text_path,
        )

    async def update_document(
        self, *, document_id: uuid.UUID, **changes: Any
    ) -> Document:
        """Update document metadata with per-field validation."""
        document = await self._require_document(document_id)
        for field in ("original_filename", "stored_filename", "file_path"):
            if field in changes:
                changes[field] = self._validate_not_blank(changes[field], field=field)
        if "checksum_sha256" in changes:
            changes["checksum_sha256"] = self._validate_checksum(
                changes["checksum_sha256"], field="checksum_sha256"
            )
        if "size_bytes" in changes and changes["size_bytes"] <= 0:
            raise ValidationError(
                message="size_bytes must be positive",
                details=[{"field": "size_bytes", "reason": "must be positive"}],
            )
        if "category" in changes:
            changes["category"] = self._validate_enum(
                changes["category"], DocumentCategory, field="category"
            )
        if "status" in changes:
            changes["status"] = self._validate_enum(
                changes["status"], DocumentStatus, field="status"
            )
        user_id = changes.get("user_id", document.user_id)
        request_id = changes.get("request_id", document.request_id)
        message_id = changes.get("message_id", document.message_id)
        self._assert_owner(user_id, request_id, message_id)
        await self._validate_owners(user_id, request_id, message_id)
        return await self._documents.update(document, **changes)

    async def archive_document(self, *, document_id: uuid.UUID) -> Document:
        """Soft-delete a document (DATABASE_DESIGN.md §26)."""
        document = await self._require_document(document_id)
        return await self._documents.soft_delete(document)

    async def restore_document(self, *, document_id: uuid.UUID) -> Document:
        """Clear the soft-delete marker, returning the document to live."""
        document = await self._session.get(Document, document_id)
        if document is None:
            raise NotFoundError(message="Document not found")
        return await self._documents.restore(document)

    async def _validate_owners(
        self,
        user_id: uuid.UUID | None,
        request_id: uuid.UUID | None,
        message_id: uuid.UUID | None,
    ) -> None:
        """Raise 404 when a referenced owner does not exist."""
        if user_id is not None and await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        if request_id is not None and await self._requests.get_by_id(request_id) is None:
            raise NotFoundError(message="Request not found")
        if message_id is not None and await self._messages.get_by_id(message_id) is None:
            raise NotFoundError(message="Message not found")

    @staticmethod
    def _assert_owner(
        user_id: uuid.UUID | None,
        request_id: uuid.UUID | None,
        message_id: uuid.UUID | None,
    ) -> None:
        """Enforce the ``owner_check`` constraint: at least one owner is set."""
        if user_id is None and request_id is None and message_id is None:
            raise BusinessRuleError(
                message="A document must have at least one owner",
                details=[{"field": "owner", "reason": "no owner provided"}],
            )

    @staticmethod
    def _validate_checksum(checksum_sha256: str, *, field: str) -> str:
        checksum_sha256 = DocumentService._validate_not_blank(checksum_sha256, field=field)
        if len(checksum_sha256) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in checksum_sha256
        ):
            raise ValidationError(
                message=f"{field} must be a 64-character SHA-256 hex digest",
                details=[{"field": field, "reason": "not a sha256 hex digest"}],
            )
        return checksum_sha256

    async def _require_document(self, document_id: uuid.UUID) -> Document:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise NotFoundError(message="Document not found")
        return document

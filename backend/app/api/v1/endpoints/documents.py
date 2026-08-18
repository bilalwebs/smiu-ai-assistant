"""Document upload endpoints (API_SPECIFICATION.md).

Purpose:
    Handle file upload for user chat attachments. Files are stored on disk,
    metadata is persisted via ``DocumentService``, and PDF text is extracted
    for AI context injection.

Safety:
    - Authenticated user required for all operations.
    - Conversation ownership is verified before upload (when conversation_id
      is provided).
    - File type is validated (PDF only).
    - File size is validated against configurable limit.
    - Stored filenames are UUID-based (no path traversal).
    - Original filenames are never used for filesystem paths.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.config.settings import get_settings
from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.services import (
    get_conversation_repository,
    get_document_repository,
    get_document_service,
)
from app.exceptions.app_error import ForbiddenError, ValidationError
from app.models import DocumentCategory, DocumentStatus
from app.repositories import ConversationRepository, DocumentRepository
from app.schemas.documents import DocumentRead, DocumentUploadResponse
from app.schemas.response import SuccessResponse
from app.services import DocumentService
from app.services.exceptions import NotFoundError
from app.utils.file_storage import (
    compute_checksum,
    generate_stored_filename,
    save_extracted_text,
    save_file,
)
from app.utils.response import success_response
from app.utils.text_extraction import extract_text_from_pdf

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])

#: Allowed MIME types for upload.
_ALLOWED_CONTENT_TYPES = frozenset({"application/pdf"})


async def _require_owned_conversation(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    conversations: ConversationRepository,
) -> None:
    """Assert the conversation exists and belongs to the acting user."""
    conversation = await conversations.get_by_id(conversation_id)
    if conversation is None:
        raise NotFoundError(message="Conversation not found")
    if conversation.user_id != user_id:
        raise ForbiddenError(message="You do not own this conversation")


def _validate_file(filename: str, content_type: str | None, size: int) -> None:
    """Validate file type and size. Raises ValidationError on failure."""
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    if size > max_bytes:
        raise ValidationError(
            message=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
            details=[{"field": "file", "reason": "file too large"}],
        )

    if size <= 0:
        raise ValidationError(
            message="File is empty.",
            details=[{"field": "file", "reason": "empty file"}],
        )

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"pdf"}:
        raise ValidationError(
            message="Only PDF files are supported.",
            details=[{"field": "file", "reason": "unsupported file type"}],
        )

    if content_type and content_type not in _ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            message="Only PDF files are supported.",
            details=[{"field": "file", "reason": "unsupported content type"}],
        )


async def _process_upload(
    file: UploadFile,
    *,
    user_id: uuid.UUID,
    documents: DocumentService,
) -> DocumentRead:
    """Core upload logic: validate, store, extract text, create DB record."""
    filename = file.filename or "upload.pdf"
    content_type = file.content_type
    data = await file.read()
    size = len(data)

    _validate_file(filename, content_type, size)

    stored_filename = generate_stored_filename(filename)
    checksum = compute_checksum(data)
    file_path = str(await save_file(data, stored_filename))

    extracted_text_path: str | None = None
    doc_status = DocumentStatus.PENDING

    text = extract_text_from_pdf(data)
    if text:
        text_path = await save_extracted_text(stored_filename, text)
        extracted_text_path = str(text_path)
        doc_status = DocumentStatus.PROCESSED
    else:
        doc_status = DocumentStatus.FAILED

    doc = await documents.create_document(
        user_id=user_id,
        original_filename=filename,
        stored_filename=stored_filename,
        file_path=file_path,
        size_bytes=size,
        checksum_sha256=checksum,
        category=DocumentCategory.OTHER,
        content_type=content_type,
        status=doc_status,
        extracted_text_path=extracted_text_path,
    )

    return DocumentRead(
        id=doc.id,
        user_id=doc.user_id,
        category=doc.category.value,
        original_filename=doc.original_filename,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        status=doc.status.value,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post(
    "/documents/upload",
    response_model=SuccessResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file (no conversation required)",
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    documents: DocumentService = Depends(get_document_service),
) -> SuccessResponse[DocumentUploadResponse]:
    """Upload a PDF file without requiring an existing conversation.

    Used for new chats where the conversation has not been created yet.
    The document is owned by the authenticated user.
    """
    read = await _process_upload(file, user_id=current_user.user_id, documents=documents)
    return success_response(
        request,
        DocumentUploadResponse(document=read, message="File uploaded successfully"),
    )


@router.post(
    "/conversations/{conversation_id}/attachments",
    response_model=SuccessResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file attachment to a conversation",
)
async def upload_attachment(
    conversation_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    documents: DocumentService = Depends(get_document_service),
) -> SuccessResponse[DocumentUploadResponse]:
    """Upload a PDF file as a conversation attachment.

    Verifies conversation ownership before storing the file.
    """
    await _require_owned_conversation(
        conversation_id, current_user.user_id, conversations
    )
    read = await _process_upload(file, user_id=current_user.user_id, documents=documents)
    return success_response(
        request,
        DocumentUploadResponse(document=read, message="File uploaded successfully"),
    )


@router.get(
    "/conversations/{conversation_id}/attachments",
    response_model=SuccessResponse[list[DocumentRead]],
    summary="List attachments for a conversation",
)
async def list_attachments(
    conversation_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
) -> SuccessResponse[list[DocumentRead]]:
    """List all documents uploaded by the acting user."""
    await _require_owned_conversation(
        conversation_id, current_user.user_id, conversations
    )

    docs = await document_repo.list_by_user(current_user.user_id)
    reads = [
        DocumentRead(
            id=d.id,
            user_id=d.user_id,
            category=d.category.value,
            original_filename=d.original_filename,
            content_type=d.content_type,
            size_bytes=d.size_bytes,
            status=d.status.value,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in docs
    ]
    return success_response(request, reads)

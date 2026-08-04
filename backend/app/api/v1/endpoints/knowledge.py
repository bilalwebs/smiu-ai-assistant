"""Knowledge base endpoints (API_SPECIFICATION.md §23).

Purpose:
    Read-side knowledge access for authenticated users: indexed document
    metadata and a document's retrievable chunks/sources. Ingestion and admin
    uploads stay out of scope until the admin phase (§23.1).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.services import (
    get_knowledge_chunk_repository,
    get_knowledge_document_repository,
)
from app.repositories import (
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)
from app.schemas.knowledge import KnowledgeChunkRead, KnowledgeDocumentRead
from app.schemas.response import SuccessResponse
from app.services.exceptions import NotFoundError
from app.utils.response import success_response

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get(
    "/documents",
    response_model=SuccessResponse[list[KnowledgeDocumentRead]],
    summary="List indexed documents",
)
async def list_documents(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
    documents: KnowledgeDocumentRepository = Depends(
        get_knowledge_document_repository
    ),
) -> SuccessResponse[list[KnowledgeDocumentRead]]:
    """List live, active indexed documents, newest first (§23)."""
    items = await documents.get_active_documents(limit=limit, offset=offset)
    return success_response(
        request, [KnowledgeDocumentRead.model_validate(item) for item in items]
    )


@router.get(
    "/documents/{document_id}",
    response_model=SuccessResponse[KnowledgeDocumentRead],
    summary="Fetch document metadata",
)
async def get_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    documents: KnowledgeDocumentRepository = Depends(
        get_knowledge_document_repository
    ),
) -> SuccessResponse[KnowledgeDocumentRead]:
    """Return a document's metadata and source details (§23)."""
    document = await documents.get_by_id(document_id)
    if document is None:
        raise NotFoundError(message="Knowledge document not found")
    return success_response(request, KnowledgeDocumentRead.model_validate(document))


@router.get(
    "/documents/{document_id}/sources",
    response_model=SuccessResponse[list[KnowledgeChunkRead]],
    summary="Retrieve a document's chunks/sources",
)
async def get_document_sources(
    document_id: uuid.UUID,
    request: Request,
    limit: int = 200,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
    documents: KnowledgeDocumentRepository = Depends(
        get_knowledge_document_repository
    ),
    chunks: KnowledgeChunkRepository = Depends(get_knowledge_chunk_repository),
) -> SuccessResponse[list[KnowledgeChunkRead]]:
    """Return a document's chunks in index order (§23)."""
    document = await documents.get_by_id(document_id)
    if document is None:
        raise NotFoundError(message="Knowledge document not found")
    items = await chunks.list_by_document(document_id, limit=limit, offset=offset)
    return success_response(
        request, [KnowledgeChunkRead.model_validate(item) for item in items]
    )

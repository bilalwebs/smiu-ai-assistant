"""Admin endpoints (API_SPECIFICATION.md §25; §4.3 RBAC).

Purpose:
    Read-side admin surface demonstrating role-based authorization. Every route
    requires an access token whose ``role`` claim is ``admin`` — enforced by
    :func:`app.dependencies.rbac.require_permission`, which raises ``403`` for
    authenticated non-admins and ``401`` for unauthenticated callers.

    Scope note: knowledge-base *ingestion* and re-indexing belong to the AI/RAG
    milestone and are intentionally not implemented here; the admin knowledge
    route is the read-side listing.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import CurrentUser
from app.dependencies.rbac import require_permission
from app.dependencies.services import (
    get_audit_log_service,
    get_knowledge_document_service,
    get_user_repository,
    get_user_service,
)
from app.repositories import UserRepository
from app.schemas.audit import AuditLogRead
from app.schemas.knowledge import KnowledgeDocumentRead
from app.schemas.response import SuccessResponse
from app.schemas.users import UserRead
from app.services import (
    AuditLogService,
    KnowledgeDocumentService,
    UserService,
)
from app.services.exceptions import NotFoundError
from app.utils.response import pagination_meta, success_response

router = APIRouter(prefix="/admin", tags=["admin"])

#: Dependency guards reused across the router.
admin = Depends(require_permission("users:list"))
audit_guard = Depends(require_permission("audit_logs:read"))
knowledge_guard = Depends(require_permission("knowledge:manage"))


@router.get(
    "/users",
    response_model=SuccessResponse[list[UserRead]],
    summary="List all users (admin)",
)
async def list_users(
    request: Request,
    page: int = 1,
    limit: int = 20,
    _: CurrentUser = admin,
    service: UserService = Depends(get_user_service),
) -> SuccessResponse[list[UserRead]]:
    """Paginate all accounts, newest first (§25)."""
    page_result = await service.list_users(page=page, limit=limit)
    return success_response(
        request,
        [UserRead.model_validate(item) for item in page_result.items],
        pagination=pagination_meta(page_result),
    )


@router.get(
    "/users/{user_id}",
    response_model=SuccessResponse[UserRead],
    summary="Fetch one user (admin)",
)
async def get_user(
    user_id: uuid.UUID,
    request: Request,
    _: CurrentUser = admin,
    users: UserRepository = Depends(get_user_repository),
) -> SuccessResponse[UserRead]:
    """Return a single account by id (§25)."""
    user = await users.get_by_id(user_id)
    if user is None:
        raise NotFoundError(message="User not found")
    return success_response(request, UserRead.model_validate(user))


@router.get(
    "/audit-logs",
    response_model=SuccessResponse[list[AuditLogRead]],
    summary="View the audit trail (admin)",
)
async def list_audit_logs(
    request: Request,
    page: int = 1,
    limit: int = 20,
    _: CurrentUser = audit_guard,
    service: AuditLogService = Depends(get_audit_log_service),
) -> SuccessResponse[list[AuditLogRead]]:
    """Paginate the append-only audit trail, newest first (§24, §25)."""
    page_result = await service.list_logs(page=page, limit=limit)
    return success_response(
        request,
        [AuditLogRead.model_validate(item) for item in page_result.items],
        pagination=pagination_meta(page_result),
    )


@router.get(
    "/knowledge/documents",
    response_model=SuccessResponse[list[KnowledgeDocumentRead]],
    summary="List knowledge documents (admin)",
)
async def list_knowledge_documents(
    request: Request,
    page: int = 1,
    limit: int = 20,
    _: CurrentUser = knowledge_guard,
    service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
) -> SuccessResponse[list[KnowledgeDocumentRead]]:
    """Paginate all knowledge documents, including archived, newest first (§25)."""
    page_result = await service.list_documents(page=page, limit=limit)
    return success_response(
        request,
        [KnowledgeDocumentRead.model_validate(item) for item in page_result.items],
        pagination=pagination_meta(page_result),
    )

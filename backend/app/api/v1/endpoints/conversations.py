"""Conversation endpoints (API_SPECIFICATION.md §20, §22).

Purpose:
    Owner-scoped AI chat-session lifecycle: creation, listing, metadata
    updates, archive/restore, and soft-delete. Message-send and history live
    in :mod:`app.api.v1.endpoints.messages`.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.services import (
    get_conversation_repository,
    get_conversation_service,
)
from app.exceptions.app_error import ForbiddenError
from app.models import AIConversation
from app.repositories import ConversationRepository
from app.schemas.conversations import ConversationCreate, ConversationRead, ConversationUpdate
from app.schemas.response import SuccessResponse
from app.services import ConversationService
from app.services.exceptions import NotFoundError
from app.utils.response import pagination_meta, success_response

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def _require_owned_conversation(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    conversations: ConversationRepository,
) -> AIConversation:
    """Fetch a conversation and assert the acting user owns it."""
    conversation = await conversations.get_by_id(conversation_id)
    if conversation is None:
        raise NotFoundError(message="Conversation not found")
    if conversation.user_id != user_id:
        raise ForbiddenError(message="You do not own this conversation")
    return conversation


@router.post(
    "",
    response_model=SuccessResponse[ConversationRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_conversation(
    payload: ConversationCreate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[ConversationRead]:
    """Create a conversation owned by the acting user (§20)."""
    created = await service.create_conversation(
        user_id=current_user.user_id, **payload.model_dump()
    )
    return success_response(request, ConversationRead.model_validate(created))


@router.get(
    "",
    response_model=SuccessResponse[list[ConversationRead]],
    summary="List own conversations",
)
async def list_conversations(
    request: Request,
    page: int = 1,
    limit: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[list[ConversationRead]]:
    """Paginate the acting user's conversations, most recently active first (§22)."""
    page_result = await service.list_user_conversations(
        user_id=current_user.user_id, page=page, limit=limit
    )
    return success_response(
        request,
        [ConversationRead.model_validate(item) for item in page_result.items],
        pagination=pagination_meta(page_result),
    )


@router.get(
    "/{conversation_id}",
    response_model=SuccessResponse[ConversationRead],
    summary="Conversation details",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> SuccessResponse[ConversationRead]:
    """Return an owned conversation's details (§22)."""
    await _require_owned_conversation(
        conversation_id, current_user.user_id, conversations
    )
    entity = await service.get_conversation(conversation_id=conversation_id)
    return success_response(request, ConversationRead.model_validate(entity))


@router.patch(
    "/{conversation_id}",
    response_model=SuccessResponse[ConversationRead],
    summary="Rename / update a conversation",
)
async def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> SuccessResponse[ConversationRead]:
    """Update an owned conversation's metadata (§20, §22)."""
    await _require_owned_conversation(
        conversation_id, current_user.user_id, conversations
    )
    entity = await service.update_conversation(
        conversation_id=conversation_id, **payload.model_dump(exclude_unset=True)
    )
    return success_response(request, ConversationRead.model_validate(entity))


@router.delete(
    "/{conversation_id}",
    response_model=SuccessResponse[ConversationRead],
    summary="Soft-delete a conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> SuccessResponse[ConversationRead]:
    """Soft-delete an owned conversation (§20; DATABASE_DESIGN.md §26)."""
    await _require_owned_conversation(
        conversation_id, current_user.user_id, conversations
    )
    entity = await service.delete_conversation(conversation_id=conversation_id)
    return success_response(request, ConversationRead.model_validate(entity))


@router.post(
    "/{conversation_id}/archive",
    response_model=SuccessResponse[ConversationRead],
    summary="Archive an active conversation",
)
async def archive_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> SuccessResponse[ConversationRead]:
    """Archive an owned active conversation (§22)."""
    await _require_owned_conversation(
        conversation_id, current_user.user_id, conversations
    )
    entity = await service.archive_conversation(conversation_id=conversation_id)
    return success_response(request, ConversationRead.model_validate(entity))


@router.post(
    "/{conversation_id}/restore",
    response_model=SuccessResponse[ConversationRead],
    summary="Restore an archived conversation",
)
async def restore_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> SuccessResponse[ConversationRead]:
    """Restore an owned archived conversation (§22)."""
    await _require_owned_conversation(
        conversation_id, current_user.user_id, conversations
    )
    entity = await service.restore_conversation(conversation_id=conversation_id)
    return success_response(request, ConversationRead.model_validate(entity))

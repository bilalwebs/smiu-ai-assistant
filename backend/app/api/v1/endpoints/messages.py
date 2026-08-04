"""Chat message endpoints (API_SPECIFICATION.md §20).

Purpose:
    Owner-scoped message send and history within a conversation. The current
    phase persists user messages only; AI reply generation plugs in behind the
    agentic boundary later (AI_ARCHITECTURE.md §2).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.services import (
    get_chat_history_service,
    get_conversation_repository,
)
from app.models import MessageRole, MessageStatus
from app.repositories import ConversationRepository
from app.schemas.messages import MessageRead, MessageSend
from app.schemas.response import SuccessResponse
from app.services import ChatHistoryService
from app.services.exceptions import NotFoundError
from app.utils.response import success_response

router = APIRouter(tags=["messages"])


async def _require_owned_conversation(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    conversations: ConversationRepository,
) -> None:
    """Assert the acting user owns the conversation (raise 404 when missing)."""
    conversation = await conversations.get_by_id(conversation_id)
    if conversation is None:
        raise NotFoundError(message="Conversation not found")
    if conversation.user_id != user_id:
        raise NotFoundError(message="Conversation not found")


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SuccessResponse[MessageRead],
    status_code=status.HTTP_201_CREATED,
    summary="Send a message in a conversation",
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageSend,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> SuccessResponse[MessageRead]:
    """Append a user message to an owned active conversation (§20)."""
    await _require_owned_conversation(
        conversation_id, current_user.user_id, conversations
    )
    message = await service.add_message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=payload.content,
        content_format=payload.content_format,
        status=MessageStatus.COMPLETED,
        parent_message_id=payload.parent_message_id,
    )
    return success_response(request, MessageRead.model_validate(message))


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=SuccessResponse[list[MessageRead]],
    summary="Fetch the conversation message history",
)
async def get_message_history(
    conversation_id: uuid.UUID,
    request: Request,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> SuccessResponse[list[MessageRead]]:
    """Return an owned conversation's messages in chronological order (§20)."""
    await _require_owned_conversation(
        conversation_id, current_user.user_id, conversations
    )
    history = await service.get_history(conversation_id=conversation_id, limit=limit)
    return success_response(
        request, [MessageRead.model_validate(message) for message in history]
    )

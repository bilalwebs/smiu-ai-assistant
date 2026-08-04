"""AI-adjacent endpoints (API_SPECIFICATION.md §21).

Purpose:
    Expose the AI-adjacent surfaces the current phase supports: citation
    sources per message and user feedback submission/triage. The ``/ai/chat``
    agentic boundary remains out of scope until the LLM layer lands
    (AI_ARCHITECTURE.md §2); feedback references are owner-scoped.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.services import (
    get_ai_source_service,
    get_chat_message_repository,
    get_conversation_repository,
    get_feedback_repository,
    get_feedback_service,
)
from app.repositories import (
    ChatMessageRepository,
    ConversationRepository,
    FeedbackRepository,
)
from app.schemas.ai import (
    AISourceRead,
    FeedbackRead,
    FeedbackStatusUpdate,
    FeedbackSubmit,
)
from app.schemas.response import SuccessResponse
from app.services import AISourceService, FeedbackService
from app.services.exceptions import NotFoundError
from app.utils.response import success_response

router = APIRouter(prefix="/ai", tags=["ai"])


async def _require_owned_message(
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    messages: ChatMessageRepository,
    conversations: ConversationRepository,
) -> None:
    """Assert the message belongs to a conversation the acting user owns."""
    message = await messages.get_by_id(message_id)
    if message is None:
        raise NotFoundError(message="Message not found")
    conversation = await conversations.get_by_id(message.conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise NotFoundError(message="Message not found")


@router.get(
    "/sources/{message_id}",
    response_model=SuccessResponse[list[AISourceRead]],
    summary="Retrieve citation sources for a message",
)
async def get_sources(
    message_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AISourceService = Depends(get_ai_source_service),
    messages: ChatMessageRepository = Depends(get_chat_message_repository),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> SuccessResponse[list[AISourceRead]]:
    """Return the citations attached to an owned message (§21.4)."""
    await _require_owned_message(
        message_id, current_user.user_id, messages, conversations
    )
    sources = await service.list_sources(message_id=message_id)
    return success_response(
        request, [AISourceRead.model_validate(source) for source in sources]
    )


@router.post(
    "/feedback",
    response_model=SuccessResponse[FeedbackRead],
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback for an AI message",
)
async def submit_feedback(
    payload: FeedbackSubmit,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
    messages: ChatMessageRepository = Depends(get_chat_message_repository),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> SuccessResponse[FeedbackRead]:
    """Submit a rating/comment/flag on an AI message (§21.5)."""
    if payload.message_id is not None:
        await _require_owned_message(
            payload.message_id, current_user.user_id, messages, conversations
        )
    elif payload.conversation_id is not None:
        conversation = await conversations.get_by_id(payload.conversation_id)
        if conversation is None or conversation.user_id != current_user.user_id:
            raise NotFoundError(message="Conversation not found")
    feedback = await service.submit_feedback(
        user_id=current_user.user_id, **payload.model_dump()
    )
    return success_response(request, FeedbackRead.model_validate(feedback))


@router.patch(
    "/feedback/{feedback_id}/status",
    response_model=SuccessResponse[FeedbackRead],
    summary="Transition feedback through triage states",
)
async def update_feedback_status(
    feedback_id: uuid.UUID,
    payload: FeedbackStatusUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
    feedback: FeedbackRepository = Depends(get_feedback_repository),
) -> SuccessResponse[FeedbackRead]:
    """Transition an owned feedback through the triage state machine (§23)."""
    entity = await feedback.get_by_id(feedback_id)
    if entity is None:
        raise NotFoundError(message="Feedback not found")
    if entity.user_id != current_user.user_id:
        raise NotFoundError(message="Feedback not found")
    updated = await service.update_status(
        feedback_id=feedback_id,
        status=payload.status,
        resolution_notes=payload.resolution_notes,
    )
    return success_response(request, FeedbackRead.model_validate(updated))

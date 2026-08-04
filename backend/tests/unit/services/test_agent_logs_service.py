"""``agent_logs`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import AgentKey, AgentRunStatus, MessageRole
from app.services import AgentLogService
from app.services.exceptions import NotFoundError, ValidationError


async def _conversation_and_message(conversation_service, chat_history_service, user_factory):
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    message = await chat_history_service.add_message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content="When do applications close?",
    )
    return user, conversation, message


async def test_create_log_happy_path(
    conversation_service, chat_history_service, agent_log_service, user_factory
) -> None:
    user, conversation, message = await _conversation_and_message(
        conversation_service, chat_history_service, user_factory
    )
    log = await agent_log_service.create_log(
        run_status=AgentRunStatus.SUCCESS,
        user_id=user.id,
        conversation_id=conversation.id,
        message_id=message.id,
        agent_key=AgentKey.ADMISSION,
        intent="deadline_inquiry",
        confidence=0.92,
        model="gpt-4o",
        token_usage={"prompt_tokens": 100, "completion_tokens": 40},
        latency_ms=850,
        retry_count=0,
        metadata_={"sources_used": 2},
    )
    assert log.agent_key == AgentKey.ADMISSION
    assert log.run_status == AgentRunStatus.SUCCESS
    assert log.confidence == 0.92
    assert log.retry_count == 0


async def test_create_log_failed_run(
    conversation_service, chat_history_service, agent_log_service, user_factory
) -> None:
    user, conversation, _ = await _conversation_and_message(
        conversation_service, chat_history_service, user_factory
    )
    log = await agent_log_service.create_log(
        run_status=AgentRunStatus.FAILED,
        user_id=user.id,
        conversation_id=conversation.id,
        agent_key=AgentKey.FAQ,
        error_code="retrieval_timeout",
        retry_count=3,
    )
    assert log.run_status == AgentRunStatus.FAILED
    assert log.error_code == "retrieval_timeout"
    assert log.retry_count == 3


async def test_create_log_without_references(
    agent_log_service: AgentLogService,
) -> None:
    log = await agent_log_service.create_log(
        run_status=AgentRunStatus.SUCCESS, agent_key=AgentKey.COORDINATOR
    )
    assert log.user_id is None
    assert log.agent_key == AgentKey.COORDINATOR


async def test_create_log_invalid_run_status_raises(
    agent_log_service: AgentLogService,
) -> None:
    with pytest.raises(ValidationError):
        await agent_log_service.create_log(run_status="bogus")


async def test_create_log_invalid_agent_key_raises(
    agent_log_service: AgentLogService,
) -> None:
    with pytest.raises(ValidationError):
        await agent_log_service.create_log(
            run_status=AgentRunStatus.SUCCESS, agent_key="bogus"
        )


async def test_create_log_confidence_out_of_range_raises(
    agent_log_service: AgentLogService,
) -> None:
    with pytest.raises(ValidationError):
        await agent_log_service.create_log(
            run_status=AgentRunStatus.SUCCESS, confidence=1.1
        )


async def test_create_log_negative_latency_raises(
    agent_log_service: AgentLogService,
) -> None:
    with pytest.raises(ValidationError):
        await agent_log_service.create_log(
            run_status=AgentRunStatus.SUCCESS, latency_ms=-1
        )


async def test_create_log_negative_retry_raises(
    agent_log_service: AgentLogService,
) -> None:
    with pytest.raises(ValidationError):
        await agent_log_service.create_log(
            run_status=AgentRunStatus.SUCCESS, retry_count=-1
        )


async def test_create_log_missing_user_raises(
    agent_log_service: AgentLogService,
) -> None:
    with pytest.raises(NotFoundError):
        await agent_log_service.create_log(
            run_status=AgentRunStatus.SUCCESS, user_id=uuid.uuid4()
        )


async def test_create_log_missing_conversation_raises(
    agent_log_service: AgentLogService,
) -> None:
    with pytest.raises(NotFoundError):
        await agent_log_service.create_log(
            run_status=AgentRunStatus.SUCCESS, conversation_id=uuid.uuid4()
        )


async def test_create_log_missing_message_raises(
    agent_log_service: AgentLogService,
) -> None:
    with pytest.raises(NotFoundError):
        await agent_log_service.create_log(
            run_status=AgentRunStatus.SUCCESS, message_id=uuid.uuid4()
        )


async def test_list_by_conversation_returns_newest_first(
    conversation_service, chat_history_service, agent_log_service, user_factory
) -> None:
    user, conversation, _ = await _conversation_and_message(
        conversation_service, chat_history_service, user_factory
    )
    await agent_log_service.create_log(
        run_status=AgentRunStatus.SUCCESS,
        user_id=user.id,
        conversation_id=conversation.id,
        intent="first",
    )
    await agent_log_service.create_log(
        run_status=AgentRunStatus.SUCCESS,
        user_id=user.id,
        conversation_id=conversation.id,
        intent="second",
    )
    logs = await agent_log_service.list_by_conversation(conversation_id=conversation.id)
    assert [log.intent for log in logs] == ["second", "first"]


async def test_list_by_conversation_excludes_other_conversations(
    conversation_service, chat_history_service, agent_log_service, user_factory
) -> None:
    user, conversation, _ = await _conversation_and_message(
        conversation_service, chat_history_service, user_factory
    )
    other = await conversation_service.create_conversation(user_id=user.id)
    await agent_log_service.create_log(
        run_status=AgentRunStatus.SUCCESS,
        user_id=user.id,
        conversation_id=conversation.id,
        intent="mine",
    )
    await agent_log_service.create_log(
        run_status=AgentRunStatus.SUCCESS,
        user_id=user.id,
        conversation_id=other.id,
        intent="theirs",
    )
    logs = await agent_log_service.list_by_conversation(conversation_id=conversation.id)
    assert [log.intent for log in logs] == ["mine"]


async def test_list_by_conversation_missing_conversation_raises(
    agent_log_service: AgentLogService,
) -> None:
    with pytest.raises(NotFoundError):
        await agent_log_service.list_by_conversation(conversation_id=uuid.uuid4())

"""Conversation memory integration tests (AI_ARCHITECTURE.md §21, §22.5, §23.1).

Step B of the AI integration boundary: session memory is rebuilt from persisted
``chat_history`` rows (short-term window + opt-in summary) and the workflow's
``persist_writer`` is wired to the backend ``ConversationMemoryWriter``. The
suite drives the facade against the real services on the shared in-memory
``db_session`` with a fully offline workflow (rule-based Coordinator + fake
specialists) and records the raw workflow input/output state so window
enforcement is asserted deterministically (TESTING_STRATEGY.md §26; §23.2).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import pytest
from ai.core.config import Settings
from ai.core.state import AgentKey as AIAgentKey
from ai.graphs.workflow import build_workflow
from ai.memory.manager import ConversationMemoryManager
from ai.tests.test_admission import FakeGateway, FakeRetriever, _chunk, _llm_json
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MessageRole
from app.schemas.ai import ChatResponse
from app.services import (
    AIChatService,
    AISourceService,
    ConversationMemoryWriter,
    ConversationService,
)

_ADMISSION_QUERY = "What are the admission requirements for BSCS?"
_ADMISSION_ANSWER = "You are eligible with 60% in intermediate."


class RecordingWorkflow:
    """Wrap the compiled graph and record raw input/output state dicts."""

    def __init__(self, graph: Any) -> None:
        self._graph = graph
        self.inputs: list[dict[str, Any]] = []
        self.outputs: list[dict[str, Any]] = []

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        self.inputs.append(state)
        result = self._graph.invoke(state)
        self.outputs.append(result)
        return result


class RaisingWriter(ConversationMemoryWriter):
    """``persist_writer`` that fails on every write (§23.1)."""

    def __call__(self, history: Any) -> None:
        raise RuntimeError("database is down")


class RecordingWriter(ConversationMemoryWriter):
    """``persist_writer`` that records every summary flush."""

    def __init__(self, conversations: ConversationService) -> None:
        super().__init__(conversations)
        self.flushes: list[tuple[uuid.UUID, str]] = []

    async def flush(self, *, conversation_id: uuid.UUID, summary: str) -> bool:
        self.flushes.append((conversation_id, summary))
        return await super().flush(conversation_id=conversation_id, summary=summary)


class FlushFailingWriter(ConversationMemoryWriter):
    """``persist_writer`` whose summary flush raises (§23.1)."""

    async def flush(self, *, conversation_id: uuid.UUID, summary: str) -> bool:
        raise RuntimeError("database is down")


class FailingConversationService:
    """Conversation service that fails every read."""

    async def get_conversation(self, *, conversation_id: uuid.UUID) -> Any:
        raise RuntimeError("database is down")


@dataclass
class Harness:
    service: AIChatService
    workflow: RecordingWorkflow
    memory: ConversationMemoryManager
    writer: ConversationMemoryWriter | None = None


def _turns(history: Any) -> list[tuple[str, str]]:
    """Normalize ``ChatTurn`` instances/dicts to ``(role, content)`` pairs."""
    normalized: list[tuple[str, str]] = []
    for turn in history:
        if isinstance(turn, dict):
            normalized.append((str(turn["role"]), turn["content"]))
        else:
            normalized.append((str(turn.role), turn.content))
    return normalized


def _build_workflow(
    *,
    memory: ConversationMemoryManager,
    writer: ConversationMemoryWriter | None,
) -> RecordingWorkflow:
    """Compile the graph offline: rule-based Coordinator + fake specialists."""
    from ai.agents.admission import create_admission_agent
    from ai.agents.coordinator import create_coordinator
    from ai.agents.examination import create_examination_agent
    from ai.agents.faq import create_faq_agent

    settings = Settings(_env_file=None)
    chunk = _chunk("abc123")
    admission = create_admission_agent(
        settings=settings,
        retriever=FakeRetriever([chunk]),
        gateway=FakeGateway(
            content=_llm_json(
                answer=_ADMISSION_ANSWER,
                cited_chunk_ids=[chunk.chunk_id],
            )
        ),
    )
    examination = create_examination_agent(
        settings=settings,
        retriever=FakeRetriever(),
        gateway=FakeGateway(
            content=_llm_json(answer="Date sheets are published per semester.")
        ),
    )
    faq = create_faq_agent(
        settings=settings,
        retriever=FakeRetriever(),
        gateway=FakeGateway(content=_llm_json(answer="The library opens at 8am.")),
    )
    graph = build_workflow(
        coordinator=create_coordinator(),
        memory=memory,
        specialists={
            AIAgentKey.ADMISSION: admission,
            AIAgentKey.EXAMINATION: examination,
            AIAgentKey.FAQ: faq,
        },
        persist_writer=writer,
    )
    return RecordingWorkflow(graph)


def _make_harness(
    db_session: AsyncSession,
    *,
    chat_history_limit: int = 4,
    writer: ConversationMemoryWriter | None = None,
) -> Harness:
    memory = ConversationMemoryManager(chat_history_limit=chat_history_limit)
    recording = _build_workflow(memory=memory, writer=writer)
    return Harness(
        service=AIChatService(
            db_session,
            workflow=recording,
            memory=memory,
            memory_writer=writer,
        ),
        workflow=recording,
        memory=memory,
        writer=writer,
    )


async def _seed_exchange(
    chat_history_service: Any,
    conversation_id: uuid.UUID,
    question: str,
    answer: str,
) -> None:
    await chat_history_service.add_message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=question,
    )
    await chat_history_service.add_message(
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content=answer,
    )


@pytest.fixture()
def make_harness(db_session: AsyncSession) -> Any:
    def _make(
        *,
        chat_history_limit: int = 4,
        writer: ConversationMemoryWriter | None = None,
    ) -> Harness:
        return _make_harness(
            db_session, chat_history_limit=chat_history_limit, writer=writer
        )

    return _make


async def test_new_conversation_starts_with_empty_memory(
    make_harness: Any,
    user_factory: Any,
) -> None:
    harness = make_harness()
    user = await user_factory()

    result = await harness.service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    assert isinstance(result, ChatResponse)
    assert result.status == "completed"
    assert harness.workflow.inputs[-1]["message_history"] == []
    assert _turns(harness.workflow.outputs[-1]["message_history"]) == [
        ("user", _ADMISSION_QUERY),
        ("assistant", _ADMISSION_ANSWER),
    ]


async def test_rebuilds_window_from_persisted_history(
    make_harness: Any,
    conversation_service: ConversationService,
    chat_history_service: Any,
    user_factory: Any,
) -> None:
    harness = make_harness()
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    await _seed_exchange(chat_history_service, conversation.id, "q1", "a1")
    await _seed_exchange(chat_history_service, conversation.id, "q2", "a2")

    result = await harness.service.chat(
        user_id=user.id,
        message=_ADMISSION_QUERY,
        conversation_id=conversation.id,
    )

    assert result.status == "completed"
    assert _turns(harness.workflow.inputs[-1]["message_history"]) == [
        ("user", "q1"),
        ("assistant", "a1"),
        ("user", "q2"),
        ("assistant", "a2"),
    ]


async def test_rebuild_preserves_turn_order(
    make_harness: Any,
    conversation_service: ConversationService,
    chat_history_service: Any,
    user_factory: Any,
) -> None:
    harness = make_harness(chat_history_limit=6)
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    await _seed_exchange(chat_history_service, conversation.id, "q1", "a1")
    await _seed_exchange(chat_history_service, conversation.id, "q2", "a2")
    await _seed_exchange(chat_history_service, conversation.id, "q3", "a3")

    await harness.service.chat(
        user_id=user.id,
        message=_ADMISSION_QUERY,
        conversation_id=conversation.id,
    )

    assert _turns(harness.workflow.inputs[-1]["message_history"]) == [
        ("user", "q1"),
        ("assistant", "a1"),
        ("user", "q2"),
        ("assistant", "a2"),
        ("user", "q3"),
        ("assistant", "a3"),
    ]


async def test_window_enforces_chat_history_limit(
    make_harness: Any,
    conversation_service: ConversationService,
    chat_history_service: Any,
    user_factory: Any,
) -> None:
    harness = make_harness(chat_history_limit=2)
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    await _seed_exchange(chat_history_service, conversation.id, "q1", "a1")
    await _seed_exchange(chat_history_service, conversation.id, "q2", "a2")
    await _seed_exchange(chat_history_service, conversation.id, "q3", "a3")

    await harness.service.chat(
        user_id=user.id,
        message=_ADMISSION_QUERY,
        conversation_id=conversation.id,
    )

    assert _turns(harness.workflow.inputs[-1]["message_history"]) == [
        ("user", "q3"),
        ("assistant", "a3"),
    ]


async def test_old_messages_beyond_window_are_excluded(
    make_harness: Any,
    conversation_service: ConversationService,
    chat_history_service: Any,
    user_factory: Any,
) -> None:
    harness = make_harness(chat_history_limit=2)
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    await _seed_exchange(chat_history_service, conversation.id, "q1", "a1")
    await _seed_exchange(chat_history_service, conversation.id, "q2", "a2")
    await _seed_exchange(chat_history_service, conversation.id, "q3", "a3")

    await harness.service.chat(
        user_id=user.id,
        message=_ADMISSION_QUERY,
        conversation_id=conversation.id,
    )

    input_history = _turns(harness.workflow.inputs[-1]["message_history"])
    assert ("user", "q1") not in input_history
    assert ("assistant", "a1") not in input_history


async def test_system_and_tool_messages_never_enter_window(
    make_harness: Any,
    conversation_service: ConversationService,
    chat_history_service: Any,
    user_factory: Any,
) -> None:
    harness = make_harness()
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    await _seed_exchange(chat_history_service, conversation.id, "q1", "a1")
    await chat_history_service.add_message(
        conversation_id=conversation.id,
        role=MessageRole.SYSTEM,
        content="system note",
    )
    await chat_history_service.add_message(
        conversation_id=conversation.id,
        role=MessageRole.TOOL,
        content="tool result",
    )

    await harness.service.chat(
        user_id=user.id,
        message=_ADMISSION_QUERY,
        conversation_id=conversation.id,
    )

    assert _turns(harness.workflow.inputs[-1]["message_history"]) == [
        ("user", "q1"),
        ("assistant", "a1"),
    ]


async def test_followup_turn_receives_prior_context(
    make_harness: Any,
    user_factory: Any,
) -> None:
    harness = make_harness()
    user = await user_factory()
    first = await harness.service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    second = await harness.service.chat(
        user_id=user.id,
        message="What is my exam result date sheet?",
        conversation_id=first.conversation_id,
    )

    assert second.status == "completed"
    assert _turns(harness.workflow.inputs[1]["message_history"]) == [
        ("user", _ADMISSION_QUERY),
        ("assistant", _ADMISSION_ANSWER),
    ]


async def test_resume_appends_without_duplicate_messages(
    make_harness: Any,
    chat_history_service: Any,
    user_factory: Any,
) -> None:
    harness = make_harness()
    user = await user_factory()
    first = await harness.service.chat(user_id=user.id, message=_ADMISSION_QUERY)
    second = await harness.service.chat(
        user_id=user.id,
        message=_ADMISSION_QUERY,
        conversation_id=first.conversation_id,
    )

    assert second.conversation_id == first.conversation_id
    history = await chat_history_service.get_history(
        conversation_id=first.conversation_id
    )
    assert [message.role for message in history] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]


async def test_no_duplicate_citations_across_runs(
    make_harness: Any,
    ai_source_service: AISourceService,
    user_factory: Any,
) -> None:
    harness = make_harness()
    user = await user_factory()
    first = await harness.service.chat(user_id=user.id, message=_ADMISSION_QUERY)
    second = await harness.service.chat(
        user_id=user.id,
        message=_ADMISSION_QUERY,
        conversation_id=first.conversation_id,
    )

    first_sources = await ai_source_service.list_sources(
        message_id=first.assistant_message_id
    )
    second_sources = await ai_source_service.list_sources(
        message_id=second.assistant_message_id
    )
    assert len(first_sources) == 1
    assert len(second_sources) == 1


async def test_persist_writer_records_post_run_window(
    db_session: AsyncSession,
    make_harness: Any,
    user_factory: Any,
) -> None:
    writer = ConversationMemoryWriter(ConversationService(db_session))
    harness = make_harness(writer=writer)
    user = await user_factory()

    result = await harness.service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    assert result.status == "completed"
    assert _turns(writer.latest_window) == [
        ("user", _ADMISSION_QUERY),
        ("assistant", _ADMISSION_ANSWER),
    ]


async def test_persist_writer_failure_never_fails_run(
    db_session: AsyncSession,
    make_harness: Any,
    user_factory: Any,
) -> None:
    writer = RaisingWriter(ConversationService(db_session))
    harness = make_harness(writer=writer)
    user = await user_factory()

    result = await harness.service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    assert result.status == "completed"
    assert result.answer == _ADMISSION_ANSWER


async def test_facade_flushes_carried_summary(
    db_session: AsyncSession,
    make_harness: Any,
    conversation_service: ConversationService,
    user_factory: Any,
) -> None:
    writer = RecordingWriter(ConversationService(db_session))
    harness = make_harness(writer=writer)
    user = await user_factory()
    conversation = await conversation_service.create_conversation(
        user_id=user.id,
        summary="Prior summary",
    )

    result = await harness.service.chat(
        user_id=user.id,
        message=_ADMISSION_QUERY,
        conversation_id=conversation.id,
    )

    assert result.status == "completed"
    assert writer.flushes == [(conversation.id, "Prior summary")]
    refreshed = await conversation_service.get_conversation(
        conversation_id=conversation.id
    )
    assert refreshed.summary == "Prior summary"


async def test_flush_writes_changed_summary(
    db_session: AsyncSession,
    conversation_service: ConversationService,
    user_factory: Any,
) -> None:
    writer = ConversationMemoryWriter(ConversationService(db_session))
    user = await user_factory()
    conversation = await conversation_service.create_conversation(
        user_id=user.id,
        summary="Old summary",
    )

    written = await writer.flush(
        conversation_id=conversation.id,
        summary="New summary",
    )

    assert written is True
    refreshed = await conversation_service.get_conversation(
        conversation_id=conversation.id
    )
    assert refreshed.summary == "New summary"


async def test_flush_failure_returns_false_and_never_raises() -> None:
    writer = ConversationMemoryWriter(FailingConversationService())

    result = await writer.flush(conversation_id=uuid.uuid4(), summary="anything")

    assert result is False


async def test_flush_failure_never_fails_run(
    db_session: AsyncSession,
    make_harness: Any,
    conversation_service: ConversationService,
    user_factory: Any,
) -> None:
    writer = FlushFailingWriter(ConversationService(db_session))
    harness = make_harness(writer=writer)
    user = await user_factory()
    conversation = await conversation_service.create_conversation(
        user_id=user.id,
        summary="Prior summary",
    )

    result = await harness.service.chat(
        user_id=user.id,
        message=_ADMISSION_QUERY,
        conversation_id=conversation.id,
    )

    assert result.status == "completed"


async def test_regression_citations_and_handoff_persist_with_memory_wired(
    make_harness: Any,
    conversation_service: ConversationService,
    chat_history_service: Any,
    ai_source_service: AISourceService,
    user_factory: Any,
) -> None:
    harness = make_harness()
    user = await user_factory()

    result = await harness.service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    assert result.status == "completed"
    assert result.active_agent is not None
    assert result.handoff is not None
    assert result.handoff.routed_to == result.active_agent
    assert len(result.citations) == 1

    conversation = await conversation_service.get_conversation(
        conversation_id=result.conversation_id
    )
    assert conversation.current_agent == result.active_agent

    history = await chat_history_service.get_history(
        conversation_id=conversation.id
    )
    assert [message.role for message in history] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert history[1].parent_message_id == history[0].id

    sources = await ai_source_service.list_sources(
        message_id=result.assistant_message_id
    )
    assert len(sources) == 1


__all__ = []

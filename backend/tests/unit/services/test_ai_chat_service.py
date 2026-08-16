"""``ai_chat`` facade tests (TESTING_STRATEGY.md §26; API_SPECIFICATION.md §21).

The facade is exercised against the real services/repos on the shared in-memory
``db_session`` with a fully offline workflow: a rule-based Coordinator and fake
retrievers/gateways (the same fakes the AI suite uses, mocked LLM §23.2).
"""

from __future__ import annotations

import uuid

import pytest
from ai.core.config import Settings
from ai.core.state import AgentKey as AIAgentKey
from ai.graphs.workflow import build_workflow
from ai.memory.manager import ConversationMemoryManager
from ai.tests.test_admission import FakeGateway, FakeRetriever, _chunk, _llm_json
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentKey,
    KnowledgeCategory,
    MessageRole,
    MessageStatus,
    SourceType,
)
from app.schemas.ai import ChatResponse
from app.services import AIChatService, AISourceService, ConversationService
from app.services.exceptions import (
    AIUnavailableError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)

_ADMISSION_QUERY = "What are the admission requirements for BSCS?"


def _build_workflow(
    *,
    retriever_chunks: list | None = None,
    admission_gateway: FakeGateway | None = None,
    memory: ConversationMemoryManager | None = None,
) -> object:
    """Compile the graph offline: rule-based Coordinator + fake specialists."""
    from ai.agents.admission import create_admission_agent
    from ai.agents.coordinator import create_coordinator
    from ai.agents.examination import create_examination_agent
    from ai.agents.faq import create_faq_agent

    settings = Settings(_env_file=None)
    chunks = retriever_chunks if retriever_chunks is not None else [_chunk("abc123")]
    resolved_gateway = admission_gateway or FakeGateway(
        content=_llm_json(
            answer="You are eligible with 60% in intermediate.",
            cited_chunk_ids=[chunk.chunk_id for chunk in chunks],
        )
    )
    admission = create_admission_agent(
        settings=settings,
        retriever=FakeRetriever(chunks),
        gateway=resolved_gateway,
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
    memory = memory or ConversationMemoryManager(
        chat_history_limit=settings.chat_history_limit
    )
    return build_workflow(
        coordinator=create_coordinator(),
        memory=memory,
        specialists={
            AIAgentKey.ADMISSION: admission,
            AIAgentKey.EXAMINATION: examination,
            AIAgentKey.FAQ: faq,
        },
    )


@pytest.fixture()
def ai_chat_service(db_session: AsyncSession) -> AIChatService:
    memory = ConversationMemoryManager(chat_history_limit=20)
    return AIChatService(
        db_session,
        workflow=_build_workflow(memory=memory),
        memory=memory,
    )


async def test_chat_new_conversation_persists_exchange(
    ai_chat_service: AIChatService,
    conversation_service: ConversationService,
    chat_history_service,
    user_factory,
) -> None:
    user = await user_factory()
    result = await ai_chat_service.chat(
        user_id=user.id, message=_ADMISSION_QUERY, user_role="student"
    )

    assert isinstance(result, ChatResponse)
    assert result.answer == "You are eligible with 60% in intermediate."
    assert result.status == "completed"
    assert result.active_agent == AgentKey.ADMISSION
    assert result.handoff is not None
    assert result.handoff.routed_to == AgentKey.ADMISSION
    assert result.handoff.previous_agent == AgentKey.COORDINATOR
    assert result.user_message_id != result.assistant_message_id
    assert len(result.citations) == 1

    conversation = await conversation_service.get_conversation(
        conversation_id=result.conversation_id
    )
    assert conversation.user_id == user.id
    assert conversation.current_agent == AgentKey.ADMISSION

    history = await chat_history_service.get_history(conversation_id=conversation.id)
    assert [message.role for message in history] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert history[0].content == _ADMISSION_QUERY
    assert history[1].agent_key == AgentKey.ADMISSION
    assert history[1].parent_message_id == history[0].id


async def test_chat_persists_citations_as_sources(
    db_session: AsyncSession,
    ai_source_service: AISourceService,
    user_factory,
) -> None:
    service = AIChatService(
        db_session,
        workflow=_build_workflow(retriever_chunks=[_chunk("abc123", score=0.8)]),
    )
    user = await user_factory()
    result = await service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    assert len(result.citations) == 1
    assert result.citations[0].source_title == "Admission Policy"
    assert result.citations[0].relevance_score == 0.8

    sources = await ai_source_service.list_sources(message_id=result.assistant_message_id)
    assert len(sources) == 1
    assert sources[0].source_type == SourceType.RAG
    assert sources[0].source_title == "Admission Policy"
    assert float(sources[0].relevance_score) == 0.8


async def test_chat_citation_resolves_knowledge_base_links(
    db_session: AsyncSession,
    ai_source_service: AISourceService,
    knowledge_document_service,
    knowledge_chunk_service,
    user_factory,
) -> None:
    chunk = _chunk("vec-abc", score=0.9)
    service = AIChatService(
        db_session,
        workflow=_build_workflow(retriever_chunks=[chunk]),
        sources=AISourceService(db_session),
    )
    doc = await knowledge_document_service.create_document(
        title="Admission Guide",
        category=KnowledgeCategory.ADMISSION,
        source_path=f"admission/{uuid.uuid4().hex}.pdf",
        checksum_sha256="a" * 64,
    )
    db_chunk = await knowledge_chunk_service.create_chunk(
        knowledge_document_id=doc.id,
        chunk_index=0,
        chunk_text="Eligibility requires 60% in intermediate.",
        vector_id="vec-abc",
    )
    user = await user_factory()
    result = await service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    assert len(result.citations) == 1
    assert result.citations[0].knowledge_document_id == doc.id
    assert result.citations[0].knowledge_chunk_id == db_chunk.id

    source = (await ai_source_service.list_sources(message_id=result.assistant_message_id))[0]
    assert source.knowledge_document_id == doc.id
    assert source.knowledge_chunk_id == db_chunk.id


async def test_chat_continues_existing_conversation_with_history(
    ai_chat_service: AIChatService,
    conversation_service: ConversationService,
    chat_history_service,
    user_factory,
) -> None:
    user = await user_factory()
    first = await ai_chat_service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    second = await ai_chat_service.chat(
        user_id=user.id,
        message="What is my exam result date sheet?",
        conversation_id=first.conversation_id,
    )

    assert second.conversation_id == first.conversation_id
    assert second.status == "completed"
    assert second.active_agent == AgentKey.EXAMINATION
    assert second.handoff is not None
    assert second.handoff.previous_agent == AgentKey.ADMISSION
    assert second.handoff.routed_to == AgentKey.EXAMINATION

    history = await chat_history_service.get_history(conversation_id=first.conversation_id)
    assert [message.role for message in history] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    conversation = await conversation_service.get_conversation(
        conversation_id=first.conversation_id
    )
    assert conversation.current_agent == AgentKey.EXAMINATION


async def test_chat_ambiguous_query_returns_clarification(
    ai_chat_service: AIChatService,
    ai_source_service: AISourceService,
    user_factory,
) -> None:
    user = await user_factory()
    result = await ai_chat_service.chat(user_id=user.id, message="Hello there")

    assert result.status == "clarifying"
    assert result.active_agent is None
    assert result.handoff is None
    assert "rephrase" in result.answer.lower()
    assert result.citations == []

    sources = await ai_source_service.list_sources(message_id=result.assistant_message_id)
    assert sources == []


async def test_chat_unanswerable_returns_no_answer_policy(
    db_session: AsyncSession,
    ai_source_service: AISourceService,
    user_factory,
) -> None:
    workflow = _build_workflow(
        retriever_chunks=[_chunk("none", title="No matches", snippet="nothing here")],
        admission_gateway=FakeGateway(
            content=_llm_json(answer="", cited_chunk_ids=[], unanswerable=True)
        ),
    )
    service = AIChatService(db_session, workflow=workflow)
    user = await user_factory()
    result = await service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    assert result.status == "completed"
    assert result.citations == []
    assert "not available" in result.answer.lower()
    assert result.active_agent == AgentKey.ADMISSION


async def test_chat_missing_conversation_raises(
    ai_chat_service: AIChatService, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(NotFoundError):
        await ai_chat_service.chat(
            user_id=user.id,
            message="Hello",
            conversation_id=uuid.uuid4(),
        )


async def test_chat_archived_conversation_raises(
    ai_chat_service: AIChatService,
    conversation_service: ConversationService,
    user_factory,
) -> None:
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    await conversation_service.archive_conversation(conversation_id=conversation.id)

    with pytest.raises(InvalidStateError):
        await ai_chat_service.chat(
            user_id=user.id,
            message="Hello",
            conversation_id=conversation.id,
        )


async def test_chat_blank_message_raises(
    ai_chat_service: AIChatService, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await ai_chat_service.chat(user_id=user.id, message="   ")


async def test_chat_workflow_unavailable_raises_before_side_effects(
    db_session: AsyncSession,
    conversation_service: ConversationService,
    user_factory,
) -> None:
    settings = Settings(
        _env_file=None,
        vector_store_path=f"missing-index-{uuid.uuid4().hex}",
    )
    service = AIChatService(db_session, settings=settings)
    user = await user_factory()

    with pytest.raises(AIUnavailableError):
        await service.chat(user_id=user.id, message=_ADMISSION_QUERY)

    page = await conversation_service.list_user_conversations(user_id=user.id)
    assert page.total == 0


async def test_chat_message_status_is_completed(
    ai_chat_service: AIChatService, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    result = await ai_chat_service.chat(user_id=user.id, message=_ADMISSION_QUERY)
    history = await chat_history_service.get_history(conversation_id=result.conversation_id)
    assert all(message.status == MessageStatus.COMPLETED for message in history)


__all__ = []

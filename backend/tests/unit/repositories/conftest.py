"""Shared fixtures for repository tests (TESTING_STRATEGY.md §26).

Provides async entity factories that build rows through the repositories
themselves (flush, no commit) so every test exercises the real data-access path
on the shared in-memory ``db_session``.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentLog,
    AgentRunStatus,
    AIConversation,
    AISource,
    AuditLog,
    ChatMessage,
    Department,
    Document,
    Feedback,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeChunk,
    KnowledgeDocument,
    MessageRole,
    Notification,
    NotificationType,
    Request,
    RequestStatus,
    RequestTimeline,
    RequestType,
    Student,
    User,
    UserSession,
)
from app.repositories import (
    AgentLogRepository,
    AISourceRepository,
    AuditLogRepository,
    ChatMessageRepository,
    ConversationRepository,
    DepartmentRepository,
    DocumentRepository,
    FeedbackRepository,
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
    NotificationRepository,
    RequestRepository,
    RequestTimelineRepository,
    SessionRepository,
    StudentRepository,
    UserRepository,
)


@pytest.fixture()
def user_factory(db_session: AsyncSession) -> Callable[..., Awaitable[User]]:
    repo = UserRepository(db_session)

    async def _make(**overrides: Any) -> User:
        values: dict[str, Any] = {
            "email": f"{uuid.uuid4().hex}@example.com",
            "password_hash": "hashed-password",
            "full_name": "Test User",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def department_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Department]]:
    repo = DepartmentRepository(db_session)

    async def _make(**overrides: Any) -> Department:
        suffix = uuid.uuid4().hex[:6].upper()
        values: dict[str, Any] = {
            "code": f"DEP{suffix}",
            "name": f"Department {suffix}",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def student_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Student]]:
    repo = StudentRepository(db_session)

    async def _make(*, user_id: uuid.UUID, **overrides: Any) -> Student:
        values: dict[str, Any] = {
            "user_id": user_id,
            "enrollment_no": f"SMIU-{uuid.uuid4().hex[:8].upper()}",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def conversation_factory(db_session: AsyncSession) -> Callable[..., Awaitable[AIConversation]]:
    repo = ConversationRepository(db_session)

    async def _make(*, user_id: uuid.UUID, **overrides: Any) -> AIConversation:
        values: dict[str, Any] = {"user_id": user_id, "title": "New chat"}
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def message_factory(db_session: AsyncSession) -> Callable[..., Awaitable[ChatMessage]]:
    repo = ChatMessageRepository(db_session)

    async def _make(*, conversation_id: uuid.UUID, **overrides: Any) -> ChatMessage:
        values: dict[str, Any] = {
            "conversation_id": conversation_id,
            "role": MessageRole.USER,
            "content": "Hello",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def request_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Request]]:
    repo = RequestRepository(db_session)

    async def _make(*, user_id: uuid.UUID, **overrides: Any) -> Request:
        values: dict[str, Any] = {
            "request_no": f"REQ-{uuid.uuid4().hex[:8].upper()}",
            "user_id": user_id,
            "request_type": RequestType.GENERAL,
            "title": "A request",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def notification_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Notification]]:
    repo = NotificationRepository(db_session)

    async def _make(*, user_id: uuid.UUID, **overrides: Any) -> Notification:
        values: dict[str, Any] = {
            "user_id": user_id,
            "type": NotificationType.SYSTEM,
            "title": "Notice",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def session_factory(
    db_session: AsyncSession, user_factory: Callable[..., Awaitable[User]]
) -> Callable[..., Awaitable[UserSession]]:
    repo = SessionRepository(db_session)

    async def _make(*, user_id: uuid.UUID | None = None, **overrides: Any) -> UserSession:
        if user_id is None:
            user = await user_factory()
            user_id = user.id
        values: dict[str, Any] = {
            "user_id": user_id,
            "refresh_token_hash": uuid.uuid4().hex,
            "expires_at": datetime.now(UTC) + timedelta(days=30),
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def knowledge_document_factory(
    db_session: AsyncSession,
) -> Callable[..., Awaitable[KnowledgeDocument]]:
    repo = KnowledgeDocumentRepository(db_session)

    async def _make(**overrides: Any) -> KnowledgeDocument:
        values: dict[str, Any] = {
            "title": f"Doc {uuid.uuid4().hex[:6]}",
            "category": KnowledgeCategory.ADMISSION,
            "source_path": f"admission/{uuid.uuid4().hex[:6]}.pdf",
            "checksum_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def request_timeline_factory(
    db_session: AsyncSession,
) -> Callable[..., Awaitable[RequestTimeline]]:
    repo = RequestTimelineRepository(db_session)

    async def _make(*, request_id: uuid.UUID, **overrides: Any) -> RequestTimeline:
        values: dict[str, Any] = {
            "request_id": request_id,
            "to_status": RequestStatus.SUBMITTED,
            "action": "status_change",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def document_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Document]]:
    repo = DocumentRepository(db_session)

    async def _make(
        *,
        user_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        **overrides: Any,
    ) -> Document:
        suffix = uuid.uuid4().hex[:8]
        values: dict[str, Any] = {
            "user_id": user_id,
            "request_id": request_id,
            "original_filename": f"file-{suffix}.pdf",
            "stored_filename": f"stored-{suffix}.pdf",
            "file_path": f"uploads/{suffix}.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
            "checksum_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def knowledge_chunk_factory(
    db_session: AsyncSession,
) -> Callable[..., Awaitable[KnowledgeChunk]]:
    repo = KnowledgeChunkRepository(db_session)

    async def _make(
        *, knowledge_document_id: uuid.UUID, **overrides: Any
    ) -> KnowledgeChunk:
        values: dict[str, Any] = {
            "knowledge_document_id": knowledge_document_id,
            "chunk_index": 0,
            "chunk_text": "Chunk text",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def ai_source_factory(db_session: AsyncSession) -> Callable[..., Awaitable[AISource]]:
    repo = AISourceRepository(db_session)

    async def _make(*, message_id: uuid.UUID, **overrides: Any) -> AISource:
        values: dict[str, Any] = {
            "message_id": message_id,
            "source_title": f"Source {uuid.uuid4().hex[:6]}",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def feedback_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Feedback]]:
    repo = FeedbackRepository(db_session)

    async def _make(*, user_id: uuid.UUID, **overrides: Any) -> Feedback:
        values: dict[str, Any] = {
            "user_id": user_id,
            "feedback_type": FeedbackType.RATING,
            "rating": 5,
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def audit_log_factory(db_session: AsyncSession) -> Callable[..., Awaitable[AuditLog]]:
    repo = AuditLogRepository(db_session)

    async def _make(**overrides: Any) -> AuditLog:
        values: dict[str, Any] = {
            "action": "request.create",
            "resource_type": "request",
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make


@pytest.fixture()
def agent_log_factory(db_session: AsyncSession) -> Callable[..., Awaitable[AgentLog]]:
    repo = AgentLogRepository(db_session)

    async def _make(**overrides: Any) -> AgentLog:
        values: dict[str, Any] = {
            "run_status": AgentRunStatus.SUCCESS,
        }
        values.update(overrides)
        return await repo.create(**values)

    return _make

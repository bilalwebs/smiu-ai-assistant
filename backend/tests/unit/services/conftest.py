"""Shared fixtures for service tests (TESTING_STRATEGY.md §26).

Service tests drive the real service path against the shared in-memory
``db_session``; entities are created through the services themselves (flush,
no commit) so each test controls its own transaction boundary.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services import (
    AgentLogService,
    AISourceService,
    AuditLogService,
    ChatHistoryService,
    ConversationService,
    DepartmentService,
    DocumentService,
    FeedbackService,
    KnowledgeChunkService,
    KnowledgeDocumentService,
    NotificationService,
    RequestService,
    RequestTimelineService,
    SessionService,
    StudentService,
    UserService,
)


@pytest.fixture()
def user_service(db_session: AsyncSession) -> UserService:
    return UserService(db_session)


@pytest.fixture()
def student_service(db_session: AsyncSession) -> StudentService:
    return StudentService(db_session)


@pytest.fixture()
def department_service(db_session: AsyncSession) -> DepartmentService:
    return DepartmentService(db_session)


@pytest.fixture()
def session_service(db_session: AsyncSession) -> SessionService:
    return SessionService(db_session)


@pytest.fixture()
def request_service(db_session: AsyncSession) -> RequestService:
    return RequestService(db_session)


@pytest.fixture()
def conversation_service(db_session: AsyncSession) -> ConversationService:
    return ConversationService(db_session)


@pytest.fixture()
def chat_history_service(db_session: AsyncSession) -> ChatHistoryService:
    return ChatHistoryService(db_session)


@pytest.fixture()
def request_timeline_service(db_session: AsyncSession) -> RequestTimelineService:
    return RequestTimelineService(db_session)


@pytest.fixture()
def notification_service(db_session: AsyncSession) -> NotificationService:
    return NotificationService(db_session)


@pytest.fixture()
def document_service(db_session: AsyncSession) -> DocumentService:
    return DocumentService(db_session)


@pytest.fixture()
def knowledge_document_service(db_session: AsyncSession) -> KnowledgeDocumentService:
    return KnowledgeDocumentService(db_session)


@pytest.fixture()
def knowledge_chunk_service(db_session: AsyncSession) -> KnowledgeChunkService:
    return KnowledgeChunkService(db_session)


@pytest.fixture()
def ai_source_service(db_session: AsyncSession) -> AISourceService:
    return AISourceService(db_session)


@pytest.fixture()
def feedback_service(db_session: AsyncSession) -> FeedbackService:
    return FeedbackService(db_session)


@pytest.fixture()
def audit_log_service(db_session: AsyncSession) -> AuditLogService:
    return AuditLogService(db_session)


@pytest.fixture()
def agent_log_service(db_session: AsyncSession) -> AgentLogService:
    return AgentLogService(db_session)


@pytest.fixture()
def user_factory(user_service: UserService) -> Callable[..., Awaitable[User]]:
    async def _make(**overrides: Any) -> User:
        values: dict[str, Any] = {
            "email": f"{uuid.uuid4().hex}@example.com",
            "password_hash": "hashed-password",
            "full_name": "Test User",
        }
        values.update(overrides)
        return await user_service.create_user(**values)

    return _make

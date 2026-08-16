"""Request-scoped service and repository factories (BACKEND_ARCHITECTURE.md §15.2).

Purpose:
    Wire the service layer (and, where a frozen service lacks a read method,
    repositories directly) into routes via FastAPI dependency injection.
    Every factory builds on :func:`app.dependencies.database.get_db_session`,
    so all dependencies in a request share one unit of work (§12.3).

Responsibilities:
    - Expose one factory per service used by the v1 routers.
    - Expose repository factories for owner-scoped read operations the Phase 4
      services do not implement (e.g., request listing, student lookup).

Usage:
    ``service: UserService = Depends(get_user_service)``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db_session
from app.repositories import (
    ChatMessageRepository,
    ConversationRepository,
    FeedbackRepository,
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
    NotificationRepository,
    RequestRepository,
    SessionRepository,
    StudentRepository,
    UserRepository,
)
from app.services import (
    AIChatService,
    AISourceService,
    AuditLogService,
    AuthService,
    ChatHistoryService,
    ConversationService,
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

Session = Annotated[AsyncSession, Depends(get_db_session)]


# -- services ----------------------------------------------------------------

def get_auth_service(db: Session) -> AuthService:
    """Yield a request-scoped authentication service."""
    return AuthService(db)


def get_user_service(db: Session) -> UserService:
    """Yield a request-scoped user service."""
    return UserService(db)


def get_session_service(db: Session) -> SessionService:
    """Yield a request-scoped session service."""
    return SessionService(db)


def get_student_service(db: Session) -> StudentService:
    """Yield a request-scoped student service."""
    return StudentService(db)


def get_request_service(db: Session) -> RequestService:
    """Yield a request-scoped request service."""
    return RequestService(db)


def get_request_timeline_service(db: Session) -> RequestTimelineService:
    """Yield a request-scoped request-timeline service."""
    return RequestTimelineService(db)


def get_notification_service(db: Session) -> NotificationService:
    """Yield a request-scoped notification service."""
    return NotificationService(db)


def get_conversation_service(db: Session) -> ConversationService:
    """Yield a request-scoped conversation service."""
    return ConversationService(db)


def get_chat_history_service(db: Session) -> ChatHistoryService:
    """Yield a request-scoped chat-history service."""
    return ChatHistoryService(db)


def get_knowledge_document_service(db: Session) -> KnowledgeDocumentService:
    """Yield a request-scoped knowledge-document service."""
    return KnowledgeDocumentService(db)


def get_knowledge_chunk_service(db: Session) -> KnowledgeChunkService:
    """Yield a request-scoped knowledge-chunk service."""
    return KnowledgeChunkService(db)


def get_ai_source_service(db: Session) -> AISourceService:
    """Yield a request-scoped AI-source service."""
    return AISourceService(db)


def get_ai_chat_service(db: Session) -> AIChatService:
    """Yield a request-scoped AI chat service."""
    return AIChatService(db)


def get_feedback_service(db: Session) -> FeedbackService:
    """Yield a request-scoped feedback service."""
    return FeedbackService(db)


def get_audit_log_service(db: Session) -> AuditLogService:
    """Yield a request-scoped audit-log service."""
    return AuditLogService(db)


# -- repositories ------------------------------------------------------------

def get_user_repository(db: Session) -> UserRepository:
    """Yield a request-scoped user repository."""
    return UserRepository(db)


def get_session_repository(db: Session) -> SessionRepository:
    """Yield a request-scoped session repository."""
    return SessionRepository(db)


def get_student_repository(db: Session) -> StudentRepository:
    """Yield a request-scoped student repository."""
    return StudentRepository(db)


def get_request_repository(db: Session) -> RequestRepository:
    """Yield a request-scoped request repository."""
    return RequestRepository(db)


def get_notification_repository(db: Session) -> NotificationRepository:
    """Yield a request-scoped notification repository."""
    return NotificationRepository(db)


def get_knowledge_document_repository(db: Session) -> KnowledgeDocumentRepository:
    """Yield a request-scoped knowledge-document repository."""
    return KnowledgeDocumentRepository(db)


def get_knowledge_chunk_repository(db: Session) -> KnowledgeChunkRepository:
    """Yield a request-scoped knowledge-chunk repository."""
    return KnowledgeChunkRepository(db)


def get_conversation_repository(db: Session) -> ConversationRepository:
    """Yield a request-scoped conversation repository."""
    return ConversationRepository(db)


def get_chat_message_repository(db: Session) -> ChatMessageRepository:
    """Yield a request-scoped chat-message repository."""
    return ChatMessageRepository(db)


def get_feedback_repository(db: Session) -> FeedbackRepository:
    """Yield a request-scoped feedback repository."""
    return FeedbackRepository(db)

"""Repository layer (BACKEND_ARCHITECTURE.md §12).

Purpose:
    One repository per aggregate/domain entity exposing intent-named, typed
    data-access methods. Services and routers never use raw ORM sessions —
    every query flows through a repository (BACKEND_ARCHITECTURE.md §11, §12).

Usage:
    ``repo = UserRepository(session)`` where ``session`` comes from the
    request-scoped ``get_db_session`` dependency. Repositories never commit or
    roll back; the caller's unit of work owns the transaction boundary (§12.3).
"""

from app.repositories.agent_logs import AgentLogRepository
from app.repositories.ai_conversations import ConversationRepository
from app.repositories.ai_sources import AISourceRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.base import BaseRepository, KeysetPage, Page
from app.repositories.chat_history import ChatMessageRepository
from app.repositories.departments import DepartmentRepository
from app.repositories.documents import DocumentRepository
from app.repositories.feedback import FeedbackRepository
from app.repositories.knowledge_chunks import KnowledgeChunkRepository
from app.repositories.knowledge_documents import KnowledgeDocumentRepository
from app.repositories.notifications import NotificationRepository
from app.repositories.request_timeline import RequestTimelineRepository
from app.repositories.requests import RequestRepository
from app.repositories.sessions import SessionRepository
from app.repositories.students import StudentRepository
from app.repositories.users import UserRepository

__all__ = [
    "AISourceRepository",
    "AgentLogRepository",
    "AuditLogRepository",
    "BaseRepository",
    "ChatMessageRepository",
    "ConversationRepository",
    "DepartmentRepository",
    "DocumentRepository",
    "FeedbackRepository",
    "KeysetPage",
    "KnowledgeChunkRepository",
    "KnowledgeDocumentRepository",
    "NotificationRepository",
    "Page",
    "RequestRepository",
    "RequestTimelineRepository",
    "SessionRepository",
    "StudentRepository",
    "UserRepository",
]

"""Service layer (BACKEND_ARCHITECTURE.md §11).

Purpose:
    Encapsulate business rules and workflows and orchestrate repositories and
    the AI layer. Services own the unit-of-work transaction boundary —
    repositories never commit (BACKEND_ARCHITECTURE.md §11.3, §12.3, §13).

Usage:
    ``service = UserService(session)`` where ``session`` is the request-scoped
    session provided by the DI dependency (BACKEND_ARCHITECTURE.md §8.3).
"""

from app.services.agent_logs import AgentLogService
from app.services.ai_conversations import ConversationService
from app.services.ai_sources import AISourceService
from app.services.audit_logs import AuditLogService
from app.services.auth import AuthService
from app.services.base import BaseService
from app.services.chat_history import ChatHistoryService
from app.services.departments import DepartmentService
from app.services.documents import DocumentService
from app.services.email import EmailService
from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from app.services.feedback import FeedbackService
from app.services.knowledge_chunks import KnowledgeChunkService
from app.services.knowledge_documents import KnowledgeDocumentService
from app.services.notifications import NotificationService
from app.services.request_timeline import RequestTimelineService
from app.services.requests import RequestService
from app.services.sessions import SessionService
from app.services.students import StudentService
from app.services.users import UserService

__all__ = [
    "AISourceService",
    "AgentLogService",
    "AuditLogService",
    "AuthService",
    "BaseService",
    "BusinessRuleError",
    "ChatHistoryService",
    "ConflictError",
    "ConversationService",
    "DepartmentService",
    "DocumentService",
    "EmailService",
    "FeedbackService",
    "InvalidStateError",
    "KnowledgeChunkService",
    "KnowledgeDocumentService",
    "NotFoundError",
    "NotificationService",
    "RequestService",
    "RequestTimelineService",
    "SessionService",
    "StudentService",
    "UserService",
    "ValidationError",
]

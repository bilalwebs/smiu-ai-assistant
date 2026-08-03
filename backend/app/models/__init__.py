"""ORM model package (BACKEND_ARCHITECTURE.md §5.1; DATABASE_DESIGN.md §12-25).

Purpose:
    Home for SQLAlchemy 2.0 models, the reusable column mixins, shared enum
    domains, and dialect-safe column types. Importing this package registers
    every concrete model with ``app.database.base.Base.metadata`` so Alembic
    autogenerate and ``create_all`` see the complete schema.

Usage:
    ``from app.models import User`` or ``import app.models``.
"""

from app.models.agent_logs import AgentLog
from app.models.ai_conversations import AIConversation
from app.models.ai_sources import AISource
from app.models.audit_logs import AuditLog
from app.models.base import BaseModel
from app.models.chat_history import ChatMessage
from app.models.departments import Department
from app.models.documents import Document
from app.models.enums import (
    ALL_ENUM_TYPES,
    AgentKey,
    AgentRunStatus,
    ConversationStatus,
    DocumentCategory,
    DocumentStatus,
    FeedbackSentiment,
    FeedbackStatus,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeStatus,
    MessageRole,
    MessageStatus,
    NotificationPriority,
    NotificationType,
    RequestPriority,
    RequestSource,
    RequestStatus,
    RequestType,
    SourceType,
    StudentStatus,
    UserRole,
    UserStatus,
)
from app.models.feedback import Feedback
from app.models.knowledge_chunks import KnowledgeChunk
from app.models.knowledge_documents import KnowledgeDocument
from app.models.mixins import (
    AuditMixin,
    CreatedAtMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UpdatedAtMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from app.models.notifications import Notification
from app.models.request_timeline import RequestTimeline
from app.models.requests import Request
from app.models.sessions import UserSession
from app.models.students import Student
from app.models.types import IPAddress, JsonB
from app.models.users import User

__all__ = [
    "ALL_ENUM_TYPES",
    "AIConversation",
    "AISource",
    "AgentKey",
    "AgentLog",
    "AgentRunStatus",
    "AuditLog",
    "AuditMixin",
    "BaseModel",
    "ChatMessage",
    "ConversationStatus",
    "CreatedAtMixin",
    "Department",
    "Document",
    "DocumentCategory",
    "DocumentStatus",
    "Feedback",
    "FeedbackSentiment",
    "FeedbackStatus",
    "FeedbackType",
    "IPAddress",
    "JsonB",
    "KnowledgeCategory",
    "KnowledgeChunk",
    "KnowledgeDocument",
    "KnowledgeStatus",
    "MessageRole",
    "MessageStatus",
    "Notification",
    "NotificationPriority",
    "NotificationType",
    "Request",
    "RequestPriority",
    "RequestSource",
    "RequestStatus",
    "RequestTimeline",
    "RequestType",
    "SoftDeleteMixin",
    "SourceType",
    "Student",
    "StudentStatus",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "UpdatedAtMixin",
    "User",
    "UserRole",
    "UserSession",
    "UserStatus",
    "VersionMixin",
]

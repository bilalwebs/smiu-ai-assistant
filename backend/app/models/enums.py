"""Enumeration domains (DATABASE_DESIGN.md §4.3).

Purpose:
    Every domain is declared exactly once as a Python enum and a shared
    ``sa.Enum`` instance. Models reuse the shared instances so PostgreSQL emits
    a single ``CREATE TYPE`` per domain and SQLAlchemy's enum registry is never
    populated twice, while SQLite renders each as a ``VARCHAR``.
"""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum


def _values(enum_type: type[enum.Enum]) -> list[str]:
    """Return the string values stored in the database (member.value)."""
    return [str(member.value) for member in enum_type]


class UserRole(enum.StrEnum):
    """``user_role`` — access level (BACKEND_ARCHITECTURE.md §10)."""

    STUDENT = "student"
    ADMIN = "admin"
    FACULTY = "faculty"


class UserStatus(enum.StrEnum):
    """``user_status`` — account lifecycle."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class StudentStatus(enum.StrEnum):
    """``student_status`` — academic standing."""

    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    GRADUATED = "graduated"
    SUSPENDED = "suspended"
    ALUMNI = "alumni"


class ConversationStatus(enum.StrEnum):
    """``conversation_status`` — chat session lifecycle."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class MessageRole(enum.StrEnum):
    """``message_role`` — sender of a chat message."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageStatus(enum.StrEnum):
    """``message_status`` — streaming lifecycle (ui-ux-design.md §36)."""

    QUEUED = "queued"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


class AgentKey(enum.StrEnum):
    """``agent_key`` — registered agents (future agents append)."""

    COORDINATOR = "coordinator"
    ADMISSION = "admission"
    EXAMINATION = "examination"
    FAQ = "faq"


class AgentRunStatus(enum.StrEnum):
    """``agent_run_status`` — outcome of an agent execution."""

    SUCCESS = "success"
    FAILED = "failed"
    FALLBACK = "fallback"


class RequestType(enum.StrEnum):
    """``request_type`` — workflow request kind."""

    ADMISSION = "admission"
    EXAMINATION = "examination"
    GENERAL = "general"
    OTHER = "other"


class RequestStatus(enum.StrEnum):
    """``request_status`` — standardized lifecycle state."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"


class RequestPriority(enum.StrEnum):
    """``request_priority`` — urgency of a request."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RequestSource(enum.StrEnum):
    """``request_source`` — how the request was created."""

    MANUAL = "manual"
    CHAT = "chat"


class NotificationType(enum.StrEnum):
    """``notification_type`` — notification category."""

    REQUEST = "request"
    AI = "ai"
    SYSTEM = "system"


class NotificationPriority(enum.StrEnum):
    """``notification_priority`` — drives badge/sort/toast behavior."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DocumentCategory(enum.StrEnum):
    """``document_category`` — document classification."""

    ADMISSION = "admission"
    EXAMINATION = "examination"
    STUDENT = "student"
    REQUEST_ATTACHMENT = "request_attachment"
    IDENTITY = "identity"
    OTHER = "other"


class DocumentStatus(enum.StrEnum):
    """``document_status`` — processing state."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class KnowledgeCategory(enum.StrEnum):
    """``knowledge_category`` — matches ``knowledge/`` folders."""

    ADMISSION = "admission"
    EXAMINATION = "examination"
    FAQ = "faq"
    DOCUMENTS = "documents"


class KnowledgeStatus(enum.StrEnum):
    """``knowledge_status`` — ingestion lifecycle."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    ARCHIVED = "archived"


class SourceType(enum.StrEnum):
    """``source_type`` — how a citation was produced."""

    RAG = "rag"
    MANUAL = "manual"
    SYSTEM = "system"


class FeedbackType(enum.StrEnum):
    """``feedback_type`` — kind of feedback on an AI message."""

    RATING = "rating"
    COMMENT = "comment"
    FLAG = "flag"


class FeedbackStatus(enum.StrEnum):
    """``feedback_status`` — triage state."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class FeedbackSentiment(enum.StrEnum):
    """``feedback_sentiment`` — optional tone classification."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


USER_ROLE: SAEnum = SAEnum(UserRole, name="user_role", values_callable=_values)
USER_STATUS: SAEnum = SAEnum(UserStatus, name="user_status", values_callable=_values)
STUDENT_STATUS: SAEnum = SAEnum(StudentStatus, name="student_status", values_callable=_values)
CONVERSATION_STATUS: SAEnum = SAEnum(
    ConversationStatus, name="conversation_status", values_callable=_values
)
MESSAGE_ROLE: SAEnum = SAEnum(MessageRole, name="message_role", values_callable=_values)
MESSAGE_STATUS: SAEnum = SAEnum(MessageStatus, name="message_status", values_callable=_values)
AGENT_KEY: SAEnum = SAEnum(AgentKey, name="agent_key", values_callable=_values)
AGENT_RUN_STATUS: SAEnum = SAEnum(AgentRunStatus, name="agent_run_status", values_callable=_values)
REQUEST_TYPE: SAEnum = SAEnum(RequestType, name="request_type", values_callable=_values)
REQUEST_STATUS: SAEnum = SAEnum(RequestStatus, name="request_status", values_callable=_values)
REQUEST_PRIORITY: SAEnum = SAEnum(RequestPriority, name="request_priority", values_callable=_values)
REQUEST_SOURCE: SAEnum = SAEnum(RequestSource, name="request_source", values_callable=_values)
NOTIFICATION_TYPE: SAEnum = SAEnum(
    NotificationType, name="notification_type", values_callable=_values
)
NOTIFICATION_PRIORITY: SAEnum = SAEnum(
    NotificationPriority, name="notification_priority", values_callable=_values
)
DOCUMENT_CATEGORY: SAEnum = SAEnum(
    DocumentCategory, name="document_category", values_callable=_values
)
DOCUMENT_STATUS: SAEnum = SAEnum(
    DocumentStatus, name="document_status", values_callable=_values
)
KNOWLEDGE_CATEGORY: SAEnum = SAEnum(
    KnowledgeCategory, name="knowledge_category", values_callable=_values
)
KNOWLEDGE_STATUS: SAEnum = SAEnum(
    KnowledgeStatus, name="knowledge_status", values_callable=_values
)
SOURCE_TYPE: SAEnum = SAEnum(
    SourceType, name="source_type", values_callable=_values
)
FEEDBACK_TYPE: SAEnum = SAEnum(
    FeedbackType, name="feedback_type", values_callable=_values
)
FEEDBACK_STATUS: SAEnum = SAEnum(
    FeedbackStatus, name="feedback_status", values_callable=_values
)
FEEDBACK_SENTIMENT: SAEnum = SAEnum(
    FeedbackSentiment, name="feedback_sentiment", values_callable=_values
)

ALL_ENUM_TYPES: tuple[SAEnum, ...] = (
    USER_ROLE,
    USER_STATUS,
    STUDENT_STATUS,
    CONVERSATION_STATUS,
    MESSAGE_ROLE,
    MESSAGE_STATUS,
    AGENT_KEY,
    AGENT_RUN_STATUS,
    REQUEST_TYPE,
    REQUEST_STATUS,
    REQUEST_PRIORITY,
    REQUEST_SOURCE,
    NOTIFICATION_TYPE,
    NOTIFICATION_PRIORITY,
    DOCUMENT_CATEGORY,
    DOCUMENT_STATUS,
    KNOWLEDGE_CATEGORY,
    KNOWLEDGE_STATUS,
    SOURCE_TYPE,
    FEEDBACK_TYPE,
    FEEDBACK_STATUS,
    FEEDBACK_SENTIMENT,
)

"""API schema package.

Purpose:
    Declare the request/response payload schemas consumed by the v1 routers
    (API_SPECIFICATION.md §7). Domain schemas subclass
    :class:`app.schemas.base.ApiModel` so ORM entities serialize consistently.
"""

from app.schemas.ai import (
    AISourceRead,
    FeedbackRead,
    FeedbackStatusUpdate,
    FeedbackSubmit,
)
from app.schemas.audit import AuditLogRead
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.base import ApiModel, UtcDateTime
from app.schemas.conversations import (
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
)
from app.schemas.knowledge import KnowledgeChunkRead, KnowledgeDocumentRead
from app.schemas.messages import MessageRead, MessageSend
from app.schemas.notifications import NotificationRead, UnreadCountRead
from app.schemas.requests import RequestCreate, RequestRead, RequestStatusUpdate, RequestUpdate
from app.schemas.response import (
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    ResponseMeta,
    SuccessResponse,
)
from app.schemas.sessions import SessionRead
from app.schemas.students import StudentDashboardRead, StudentRead, StudentUpdate
from app.schemas.timeline import TimelineEventRead
from app.schemas.users import UserRead, UserUpdate

__all__ = [
    "AISourceRead",
    "ApiModel",
    "AuditLogRead",
    "ChangePasswordRequest",
    "ConversationCreate",
    "ConversationRead",
    "ConversationUpdate",
    "ErrorBody",
    "ErrorDetail",
    "ErrorResponse",
    "FeedbackRead",
    "FeedbackStatusUpdate",
    "FeedbackSubmit",
    "ForgotPasswordRequest",
    "KnowledgeChunkRead",
    "KnowledgeDocumentRead",
    "LoginRequest",
    "MessageRead",
    "MessageSend",
    "NotificationRead",
    "PaginationMeta",
    "RefreshTokenRequest",
    "RegisterRequest",
    "RequestCreate",
    "RequestRead",
    "RequestStatusUpdate",
    "RequestUpdate",
    "ResetPasswordRequest",
    "ResponseMeta",
    "SessionRead",
    "StudentDashboardRead",
    "StudentRead",
    "StudentUpdate",
    "SuccessResponse",
    "TimelineEventRead",
    "TokenResponse",
    "UnreadCountRead",
    "UserRead",
    "UserUpdate",
    "UtcDateTime",
    "VerifyEmailRequest",
]

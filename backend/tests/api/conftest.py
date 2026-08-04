"""API-layer test fixtures (TESTING_STRATEGY.md §16).

Strategy:
    The backend runs against a shared in-memory SQLite engine (StaticPool).
    Because ``aiosqlite`` binds each operation to the *currently running*
    loop, a one-shot ``asyncio.run`` seed can create the schema and baseline
    rows before the TestClient spins up, and the app reuses the same pooled
    connection afterwards.

Fixtures:
    - ``api_client``: schema created + seeded, then a TestClient with the real
      app; caches are reset before and after.
    - ``seed_ids``: the fixed ids of every seeded row so tests can reference
      them without querying.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ["ENVIRONMENT"] = "testing"

from app.config.settings import clear_settings_cache, get_settings
from app.core.app_factory import create_app
from app.core.security.jwt import create_access_token
from app.database.base import Base
from app.database.session import get_engine, get_session_factory, reset_engine
from app.models import (
    AgentKey,
    ConversationStatus,
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
from app.repositories import (
    AISourceRepository,
    ChatMessageRepository,
    ConversationRepository,
    DepartmentRepository,
    FeedbackRepository,
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
    NotificationRepository,
    RequestRepository,
    StudentRepository,
    UserRepository,
)
from app.utils.time import utc_now

# -- fixed identities --------------------------------------------------------

OWNER_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
STUDENT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
DEPARTMENT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
DRAFT_REQUEST_ID = uuid.UUID("55555555-5555-5555-5555-555555555501")
SUBMITTED_REQUEST_ID = uuid.UUID("55555555-5555-5555-5555-555555555502")
RESOLVED_REQUEST_ID = uuid.UUID("55555555-5555-5555-5555-555555555503")
OTHER_REQUEST_ID = uuid.UUID("55555555-5555-5555-5555-555555555504")
NOTIF_UNREAD_ID = uuid.UUID("66666666-6666-6666-6666-666666666601")
NOTIF_READ_ID = uuid.UUID("66666666-6666-6666-6666-666666666602")
CONVERSATION_ID = uuid.UUID("77777777-7777-7777-7777-777777777701")
OTHER_CONVERSATION_ID = uuid.UUID("77777777-7777-7777-7777-777777777702")
MESSAGE_ID = uuid.UUID("88888888-8888-8888-8888-888888888801")
DOCUMENT_ID = uuid.UUID("99999999-9999-9999-9999-999999999901")
CHUNK_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
FEEDBACK_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture()
def auth_headers() -> Callable[[uuid.UUID], dict[str, str]]:
    """Return a callable building bearer-token headers for a user id."""

    def build(user_id: uuid.UUID) -> dict[str, str]:
        token = create_access_token(
            subject=str(user_id), role="student", settings=get_settings()
        )
        return {"Authorization": f"Bearer {token}"}

    return build


async def _insert_seed_data(session: AsyncSession) -> None:
    """Insert the baseline rows every API test relies on."""
    users = UserRepository(session)
    departments = DepartmentRepository(session)
    students = StudentRepository(session)
    requests = RequestRepository(session)
    notifications = NotificationRepository(session)
    conversations = ConversationRepository(session)
    messages = ChatMessageRepository(session)
    documents = KnowledgeDocumentRepository(session)
    chunks = KnowledgeChunkRepository(session)
    sources = AISourceRepository(session)
    feedback = FeedbackRepository(session)

    await users.create(
        id=OWNER_USER_ID,
        email="owner@example.com",
        password_hash="x",
        full_name="Owner Student",
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
    )
    await users.create(
        id=OTHER_USER_ID,
        email="other@example.com",
        password_hash="x",
        full_name="Other Student",
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
    )
    await departments.create(
        id=DEPARTMENT_ID, code="CS", name="Computer Science"
    )
    await students.create(
        id=STUDENT_ID,
        user_id=OWNER_USER_ID,
        enrollment_no="SM-2024-001",
        department_id=DEPARTMENT_ID,
        status=StudentStatus.ACTIVE,
        program_name="BS Computer Science",
        current_semester=3,
    )

    await requests.create(
        id=DRAFT_REQUEST_ID,
        request_no="REQ-000001",
        user_id=OWNER_USER_ID,
        department_id=DEPARTMENT_ID,
        request_type=RequestType.ADMISSION,
        category="documents",
        priority=RequestPriority.MEDIUM,
        status=RequestStatus.DRAFT,
        title="Draft transcript request",
        description="Needs more details.",
        source=RequestSource.MANUAL,
    )
    await requests.create(
        id=SUBMITTED_REQUEST_ID,
        request_no="REQ-000002",
        user_id=OWNER_USER_ID,
        department_id=DEPARTMENT_ID,
        request_type=RequestType.EXAMINATION,
        priority=RequestPriority.HIGH,
        status=RequestStatus.SUBMITTED,
        title="Recheck exam paper",
        source=RequestSource.MANUAL,
    )
    await requests.create(
        id=RESOLVED_REQUEST_ID,
        request_no="REQ-000003",
        user_id=OWNER_USER_ID,
        department_id=DEPARTMENT_ID,
        request_type=RequestType.GENERAL,
        priority=RequestPriority.LOW,
        status=RequestStatus.RESOLVED,
        title="Library book renewal",
        resolution_notes="Renewed for two weeks.",
        resolved_at=utc_now(),
        source=RequestSource.MANUAL,
    )
    await requests.create(
        id=OTHER_REQUEST_ID,
        request_no="REQ-000004",
        user_id=OTHER_USER_ID,
        request_type=RequestType.GENERAL,
        status=RequestStatus.SUBMITTED,
        title="Someone else's request",
        source=RequestSource.MANUAL,
    )

    await notifications.create(
        id=NOTIF_UNREAD_ID,
        user_id=OWNER_USER_ID,
        request_id=SUBMITTED_REQUEST_ID,
        type=NotificationType.REQUEST,
        priority=NotificationPriority.HIGH,
        title="Request submitted",
        body="Your request is under review.",
    )
    await notifications.create(
        id=NOTIF_READ_ID,
        user_id=OWNER_USER_ID,
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.LOW,
        title="Welcome",
        read_at=utc_now(),
    )

    await conversations.create(
        id=CONVERSATION_ID,
        user_id=OWNER_USER_ID,
        department_id=DEPARTMENT_ID,
        title="Admission help",
        status=ConversationStatus.ACTIVE,
        current_agent=AgentKey.ADMISSION,
        message_count=1,
        total_tokens=0,
    )
    await conversations.create(
        id=OTHER_CONVERSATION_ID,
        user_id=OTHER_USER_ID,
        status=ConversationStatus.ACTIVE,
        message_count=0,
        total_tokens=0,
    )
    await messages.create(
        id=MESSAGE_ID,
        conversation_id=CONVERSATION_ID,
        role=MessageRole.USER,
        content="How do I apply?",
        content_format="markdown",
        status=MessageStatus.COMPLETED,
    )

    await documents.create(
        id=DOCUMENT_ID,
        title="Admissions Handbook 2025",
        category=KnowledgeCategory.ADMISSION,
        source_path="knowledge/admission/handbook-2025.md",
        file_type="md",
        file_size=2048,
        author="Admissions Office",
        version="1",
        checksum_sha256="a" * 64,
        status=KnowledgeStatus.PROCESSED,
        chunk_count=1,
        is_active=True,
    )
    await chunks.create(
        id=CHUNK_ID,
        knowledge_document_id=DOCUMENT_ID,
        chunk_index=0,
        chunk_text="Applications open in March.",
        vector_id="vec-1",
        heading="Deadlines",
        token_count=12,
        character_count=28,
    )
    await sources.create(
        id=uuid.uuid4(),
        message_id=MESSAGE_ID,
        knowledge_document_id=DOCUMENT_ID,
        knowledge_chunk_id=CHUNK_ID,
        source_type=SourceType.RAG,
        source_title="Admissions Handbook 2025",
        source_url="/knowledge/admission/handbook-2025.md",
        category="admission",
        relevance_score=0.93,
        snippet="Applications open in March.",
    )

    await feedback.create(
        id=FEEDBACK_ID,
        user_id=OWNER_USER_ID,
        message_id=MESSAGE_ID,
        conversation_id=CONVERSATION_ID,
        feedback_type=FeedbackType.RATING,
        rating=5,
        status=FeedbackStatus.OPEN,
    )

    await session.commit()


def _seed_database() -> None:
    """Create the schema and seed baseline data in a fresh event loop."""

    async def _run() -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with get_session_factory()() as session:
            await _insert_seed_data(session)

    asyncio.run(_run())


@pytest.fixture()
def seed_ids() -> dict[str, uuid.UUID]:
    """Return the fixed ids of every seeded row."""
    return {
        "owner_user_id": OWNER_USER_ID,
        "other_user_id": OTHER_USER_ID,
        "student_id": STUDENT_ID,
        "department_id": DEPARTMENT_ID,
        "draft_request_id": DRAFT_REQUEST_ID,
        "submitted_request_id": SUBMITTED_REQUEST_ID,
        "resolved_request_id": RESOLVED_REQUEST_ID,
        "other_request_id": OTHER_REQUEST_ID,
        "notif_unread_id": NOTIF_UNREAD_ID,
        "notif_read_id": NOTIF_READ_ID,
        "conversation_id": CONVERSATION_ID,
        "other_conversation_id": OTHER_CONVERSATION_ID,
        "message_id": MESSAGE_ID,
        "document_id": DOCUMENT_ID,
        "chunk_id": CHUNK_ID,
        "feedback_id": FEEDBACK_ID,
    }


@pytest.fixture()
def api_client() -> object:
    """Yield a seeded TestClient with caches reset on teardown."""
    clear_settings_cache()
    reset_engine()
    _seed_database()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    clear_settings_cache()
    reset_engine()

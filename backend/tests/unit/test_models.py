"""Phase 2B model tests (DATABASE_DESIGN.md §8, §10, §12-25, §26).

Covers the full 16-table schema: table registration, column sets (mutable,
append-only, timestamp-only), FK/cascade contracts (§8.2), check constraints
(§10.3), partial indexes, and dialect-level behavior (enum persistence,
constraint enforcement, soft delete) against a real in-memory SQLite schema.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every model with Base.metadata)
from app.database.base import Base
from app.models import (
    Feedback,
    KnowledgeDocument,
    Request,
    Student,
    User,
    UserSession,
)

CORE_TABLES = {
    "users",
    "students",
    "departments",
    "ai_conversations",
    "chat_history",
    "requests",
    "request_timeline",
    "notifications",
    "documents",
    "knowledge_documents",
    "knowledge_chunks",
    "ai_sources",
    "feedback",
    "audit_logs",
    "agent_logs",
    "sessions",
}


def test_all_sixteen_tables_registered() -> None:
    tables = set(Base.metadata.tables)
    assert tables >= CORE_TABLES


def test_table_class_mapping() -> None:
    assert User.__tablename__ == "users"
    assert Base.metadata.tables["chat_history"].name == "chat_history"
    assert UserSession.__tablename__ == "sessions"


def _columns(table_name: str) -> set[str]:
    return set(Base.metadata.tables[table_name].columns.keys())


BASE_MODEL_COLUMNS = {"id", "created_at", "updated_at", "deleted_at", "version"}


@pytest.mark.parametrize(
    "table_name",
    [
        "users",
        "students",
        "departments",
        "ai_conversations",
        "chat_history",
        "requests",
        "documents",
        "feedback",
        "knowledge_documents",
    ],
)
def test_mutable_table_standard_column_set(table_name: str) -> None:
    assert _columns(table_name) >= BASE_MODEL_COLUMNS


@pytest.mark.parametrize(
    "table_name", ["audit_logs", "agent_logs", "request_timeline", "sessions"]
)
def test_append_only_tables_have_no_mutable_columns(table_name: str) -> None:
    columns = _columns(table_name)
    assert "updated_at" not in columns
    assert "deleted_at" not in columns
    assert "version" not in columns


def test_knowledge_chunks_timestamp_columns_only() -> None:
    assert _columns("knowledge_chunks") == {
        "id",
        "knowledge_document_id",
        "chunk_index",
        "chunk_text",
        "vector_id",
        "heading",
        "page_number",
        "token_count",
        "character_count",
        "metadata",
        "created_at",
        "updated_at",
    }


def test_reserved_metadata_attribute_maps_to_column() -> None:
    assert "metadata" in _columns("chat_history")
    assert "metadata_" not in _columns("chat_history")


# --- Foreign key / cascade catalog (§8.2) -----------------------------------


def _fk_ondelete(table_name: str, column: str) -> str | None:
    table = Base.metadata.tables[table_name]
    return next(
        fk.ondelete
        for fk in table.c[column].foreign_keys
        if fk.parent.key == column
    )


def test_cascade_catalog() -> None:
    assert _fk_ondelete("sessions", "user_id") == "CASCADE"
    assert _fk_ondelete("students", "user_id") == "CASCADE"
    assert _fk_ondelete("ai_conversations", "user_id") == "CASCADE"
    assert _fk_ondelete("chat_history", "conversation_id") == "CASCADE"
    assert _fk_ondelete("requests", "user_id") == "CASCADE"
    assert _fk_ondelete("notifications", "user_id") == "CASCADE"
    assert _fk_ondelete("feedback", "user_id") == "CASCADE"
    assert _fk_ondelete("request_timeline", "request_id") == "CASCADE"
    assert _fk_ondelete("knowledge_chunks", "knowledge_document_id") == "CASCADE"
    assert _fk_ondelete("ai_sources", "message_id") == "CASCADE"

    assert _fk_ondelete("requests", "conversation_id") == "SET NULL"
    assert _fk_ondelete("chat_history", "parent_message_id") == "SET NULL"
    assert _fk_ondelete("feedback", "message_id") == "SET NULL"
    assert _fk_ondelete("feedback", "conversation_id") == "SET NULL"
    assert _fk_ondelete("documents", "message_id") == "SET NULL"
    assert _fk_ondelete("documents", "request_id") == "SET NULL"
    assert _fk_ondelete("ai_sources", "knowledge_document_id") == "SET NULL"
    assert _fk_ondelete("ai_sources", "knowledge_chunk_id") == "SET NULL"
    assert _fk_ondelete("notifications", "request_id") == "SET NULL"
    assert _fk_ondelete("agent_logs", "message_id") == "SET NULL"
    assert _fk_ondelete("agent_logs", "user_id") == "SET NULL"
    assert _fk_ondelete("sessions", "replaced_by_session_id") == "SET NULL"


# --- Check constraints (§10.3) ----------------------------------------------


def _check_names(table_name: str) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {
        c.name
        for c in table.constraints
        if c.name and c.name.startswith("ck_")
    }


def test_check_constraint_names() -> None:
    assert "ck_students_cgpa_check" in _check_names("students")
    assert "ck_students_semester_check" in _check_names("students")
    assert "ck_chat_history_status_roles_check" in _check_names("chat_history")
    assert "ck_requests_resolved_state_check" in _check_names("requests")
    assert "ck_requests_rejected_state_check" in _check_names("requests")
    assert "ck_documents_owner_check" in _check_names("documents")
    assert "ck_documents_size_check" in _check_names("documents")
    assert "ck_ai_sources_score_check" in _check_names("ai_sources")
    assert "ck_feedback_rating_check" in _check_names("feedback")
    assert "ck_feedback_rating_type_check" in _check_names("feedback")
    assert "ck_agent_logs_confidence_check" in _check_names("agent_logs")
    assert "ck_sessions_expiry_check" in _check_names("sessions")


# --- Partial / functional indexes -------------------------------------------


def _index(table_name: str, index_name: str) -> Any:
    return next(
        idx
        for idx in Base.metadata.tables[table_name].indexes
        if idx.name == index_name
    )


def test_partial_index_where_clauses() -> None:
    assert _index("ai_sources", "ix_ai_sources_chunk_partial").unique is True
    assert (
        str(_index("ai_sources", "ix_ai_sources_chunk_partial").dialect_options["sqlite"]["where"])
        is not None
    )
    assert (
        _index("requests", "ix_requests_active_partial").dialect_options["postgresql"]["where"]
        is not None
    )
    assert (
        _index("sessions", "ix_sessions_active_partial").dialect_options["postgresql"]["where"]
        is not None
    )
    assert (
        _index("knowledge_documents", "ix_knowledge_documents_source_path_version").unique is True
    )


def test_functional_indexes_declared() -> None:
    assert "ix_ai_conversations_user_id_last_message" in {
        i.name for i in Base.metadata.tables["ai_conversations"].indexes
    }
    assert "ix_agent_logs_created_at" in {
        i.name for i in Base.metadata.tables["agent_logs"].indexes
    }
    assert "ix_requests_status_created" in {
        i.name for i in Base.metadata.tables["requests"].indexes
    }


# --- Dialect-level behavior --------------------------------------------------


def _make_user() -> User:
    return User(
        email="test@example.com",
        password_hash="hashed",
        full_name="Test User",
    )


async def test_enum_defaults_persist(db_session: AsyncSession) -> None:
    user = _make_user()
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.role == "student"
    assert user.status == "pending"


async def test_enum_values_insertable(db_session: AsyncSession) -> None:
    user = _make_user()
    user.role = "admin"
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.role == "admin"


async def test_check_constraint_cgpa_violation(db_session: AsyncSession) -> None:
    user = _make_user()
    student = Student(user=user, enrollment_no="smiu-0001", cgpa=5.0)
    db_session.add_all([user, student])
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_check_constraint_rating_violation(db_session: AsyncSession) -> None:
    user = _make_user()
    db_session.add(user)
    await db_session.commit()

    feedback = Feedback(user_id=user.id, rating=9, feedback_type="rating")
    db_session.add(feedback)
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_check_constraint_resolved_state_violation(db_session: AsyncSession) -> None:
    user = _make_user()
    db_session.add(user)
    await db_session.commit()

    request = Request(
        request_no="REQ-1",
        user_id=user.id,
        request_type="admission",
        status="resolved",
    )
    db_session.add(request)
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_check_constraint_sessions_expiry_violation(db_session: AsyncSession) -> None:
    user = _make_user()
    db_session.add(user)
    await db_session.commit()

    session = UserSession(
        user_id=user.id,
        refresh_token_hash="x" * 64,
        expires_at=datetime.now(UTC) - timedelta(days=1),  # before created_at
    )
    db_session.add(session)
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_knowledge_document_soft_delete(db_session: AsyncSession) -> None:
    doc = KnowledgeDocument(
        title="Admissions Guide",
        category="admission",
        source_path="admissions/guide.pdf",
        checksum_sha256="a" * 64,
    )
    db_session.add(doc)
    await db_session.commit()
    assert doc.is_deleted is False

    doc.soft_delete()
    await db_session.commit()
    assert doc.deleted_at is not None
    assert doc.is_deleted is True

    doc.restore()
    assert doc.deleted_at is None


async def test_metadata_column_round_trip(db_session: AsyncSession) -> None:
    user = _make_user()
    user.preferences = {"theme": "dark"}
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.preferences == {"theme": "dark"}


# --- Cascade behavior (SQLite with FK pragma) -------------------------------


def test_delete_user_cascades_to_sessions_and_feedback() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fks(dbapi_connection: Any, _: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        user = _make_user()
        session.add(user)
        session.flush()
        session.add(
            UserSession(
                user_id=user.id,
                refresh_token_hash="y" * 64,
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )
        )
        session.add(Feedback(user_id=user.id, rating=5, feedback_type="rating"))
        session.commit()

        user_id = user.id
        session.delete(user)
        session.commit()

        with engine.connect() as conn:
            sessions = conn.scalar(
                text("SELECT COUNT(*) FROM sessions WHERE user_id = :uid"),
                {"uid": str(user_id)},
            )
            feedback_rows = conn.scalar(
                text("SELECT COUNT(*) FROM feedback WHERE user_id = :uid"),
                {"uid": str(user_id)},
            )
        assert sessions == 0
        assert feedback_rows == 0
    engine.dispose()

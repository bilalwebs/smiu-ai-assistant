"""``ai_sources`` model (DATABASE_DESIGN.md §22).

AI & Knowledge: citations attached to assistant messages. Enforces the "always
cite RAG sources" rule and powers the collapsible "Sources: 2" UI.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import SOURCE_TYPE, SourceType
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chat_history import ChatMessage
    from app.models.knowledge_chunks import KnowledgeChunk
    from app.models.knowledge_documents import KnowledgeDocument


class AISource(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A citation linking an assistant message to a knowledge source (§22)."""

    __tablename__ = "ai_sources"

    message_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("chat_history.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_document_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("knowledge_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    knowledge_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("knowledge_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[SourceType] = mapped_column(
        SOURCE_TYPE, nullable=False, server_default=sa.text("'rag'")
    )
    source_title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    category: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(
        sa.Numeric(4, 3), nullable=True
    )
    snippet: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        sa.Index("ix_ai_sources_message_id", "message_id"),
        sa.Index(
            "ix_ai_sources_chunk_partial",
            "message_id",
            "knowledge_chunk_id",
            unique=True,
            postgresql_where=sa.text("knowledge_chunk_id IS NOT NULL"),
            sqlite_where=sa.text("knowledge_chunk_id IS NOT NULL"),
        ),
        sa.CheckConstraint(
            "relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)",
            name="score_check",
        ),
    )

    message: Mapped[ChatMessage] = relationship(
        foreign_keys=[message_id], overlaps="ai_sources"
    )
    knowledge_document: Mapped[KnowledgeDocument | None] = relationship(
        foreign_keys=[knowledge_document_id], overlaps="ai_sources"
    )
    knowledge_chunk: Mapped[KnowledgeChunk | None] = relationship(
        foreign_keys=[knowledge_chunk_id]
    )

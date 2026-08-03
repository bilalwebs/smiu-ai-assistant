"""``knowledge_chunks`` model (DATABASE_DESIGN.md §21.2).

AI & Knowledge: retrievable units plus FAISS mapping. No soft delete — chunks
die with their document (CASCADE).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JsonB

if TYPE_CHECKING:
    from app.models.knowledge_documents import KnowledgeDocument


class KnowledgeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A retrievable chunk of a knowledge document (DATABASE_DESIGN.md §21.2)."""

    __tablename__ = "knowledge_chunks"

    knowledge_document_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    vector_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    heading: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    page_number: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    character_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JsonB, nullable=True, server_default=sa.text("'{}'")
    )

    __table_args__ = (
        sa.Index(
            "ix_knowledge_chunks_document_id_index",
            "knowledge_document_id",
            "chunk_index",
            unique=True,
        ),
    )

    knowledge_document: Mapped[KnowledgeDocument] = relationship(
        foreign_keys=[knowledge_document_id], overlaps="chunks"
    )

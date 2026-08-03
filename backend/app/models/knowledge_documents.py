"""``knowledge_documents`` model (DATABASE_DESIGN.md §21.1).

AI & Knowledge (PROJECT_RULES.md ``knowledge_documents`` table): source
metadata for indexed RAG documents. Chunks and FAISS mapping live in
``knowledge_chunks``.

Note:
    Per §21.1 this table declares its own ``version`` column (document version,
    varchar) instead of the optimistic-lock integer from ``BaseModel`` — the
    §21.1 column list is the authoritative, full set.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import (
    KNOWLEDGE_CATEGORY,
    KNOWLEDGE_STATUS,
    KnowledgeCategory,
    KnowledgeStatus,
)
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JsonB

if TYPE_CHECKING:
    from app.models.ai_sources import AISource
    from app.models.knowledge_chunks import KnowledgeChunk


class KnowledgeDocument(
    UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base
):
    """Metadata for an indexed RAG source document (DATABASE_DESIGN.md §21.1)."""

    __tablename__ = "knowledge_documents"

    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    category: Mapped[KnowledgeCategory] = mapped_column(
        KNOWLEDGE_CATEGORY, nullable=False
    )
    source_path: Mapped[str] = mapped_column(sa.Text, nullable=False)
    file_type: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    file_size: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    author: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    version: Mapped[str] = mapped_column(
        sa.String(30), nullable=False, server_default=sa.text("'1'")
    )
    checksum_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    status: Mapped[KnowledgeStatus] = mapped_column(
        KNOWLEDGE_STATUS, nullable=False, server_default=sa.text("'pending'")
    )
    chunk_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JsonB, nullable=True, server_default=sa.text("'{}'")
    )
    indexed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        sa.Index("ix_knowledge_documents_category_status", "category", "status"),
        sa.Index(
            "ix_knowledge_documents_source_path_version",
            "source_path",
            "version",
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
            sqlite_where=sa.text("deleted_at IS NULL"),
        ),
    )

    chunks: Mapped[list[KnowledgeChunk]] = relationship(
        passive_deletes=True, overlaps="knowledge_document"
    )
    ai_sources: Mapped[list[AISource]] = relationship(overlaps="knowledge_document")

"""``documents`` model (DATABASE_DESIGN.md §20).

Workflow & Support: metadata for uploaded files (request attachments, identity
documents, chat attachments). File bytes live on a dedicated storage path;
only metadata is stored in the database.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import BaseModel
from app.models.enums import DOCUMENT_CATEGORY, DOCUMENT_STATUS, DocumentCategory, DocumentStatus

if TYPE_CHECKING:
    from app.models.chat_history import ChatMessage
    from app.models.requests import Request
    from app.models.users import User


class Document(BaseModel, Base):
    """Uploaded file metadata (DATABASE_DESIGN.md §20)."""

    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("chat_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[DocumentCategory] = mapped_column(
        DOCUMENT_CATEGORY, nullable=False, server_default=sa.text("'other'")
    )
    original_filename: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(sa.Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        DOCUMENT_STATUS, nullable=False, server_default=sa.text("'pending'")
    )
    extracted_text_path: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (
        sa.Index("ix_documents_user_id", "user_id"),
        sa.Index("ix_documents_request_id", "request_id"),
        sa.CheckConstraint(
            "user_id IS NOT NULL OR request_id IS NOT NULL OR message_id IS NOT NULL",
            name="owner_check",
        ),
        sa.CheckConstraint("size_bytes > 0", name="size_check"),
    )

    user: Mapped[User | None] = relationship(foreign_keys=[user_id], overlaps="documents")
    request: Mapped[Request | None] = relationship(
        foreign_keys=[request_id], overlaps="documents"
    )
    message: Mapped[ChatMessage | None] = relationship(
        foreign_keys=[message_id], overlaps="documents"
    )

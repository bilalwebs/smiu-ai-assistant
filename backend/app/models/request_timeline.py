"""``request_timeline`` model (DATABASE_DESIGN.md §18).

Append-only history of every status transition on a request. Drives the
timeline UI and audit of workflow state. Rows are never updated or deleted.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import REQUEST_STATUS, RequestStatus
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.types import JsonB

if TYPE_CHECKING:
    from app.models.requests import Request
    from app.models.users import User


class RequestTimeline(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only status transition record (DATABASE_DESIGN.md §18)."""

    __tablename__ = "request_timeline"

    request_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[RequestStatus | None] = mapped_column(
        REQUEST_STATUS, nullable=True
    )
    to_status: Mapped[RequestStatus] = mapped_column(REQUEST_STATUS, nullable=False)
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JsonB, nullable=True, server_default=sa.text("'{}'")
    )

    __table_args__ = (
        sa.Index(
            "ix_request_timeline_request_id_created", "request_id", "created_at"
        ),
    )

    request: Mapped[Request] = relationship(foreign_keys=[request_id], overlaps="timeline")
    actor: Mapped[User | None] = relationship(foreign_keys=[actor_user_id])

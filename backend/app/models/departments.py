"""``departments`` model (DATABASE_DESIGN.md §14).

Organization: university departments and workflow routing targets. Routing is
data-driven — new departments are new rows, never code changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import BaseModel
from app.models.enums import AGENT_KEY, AgentKey

if TYPE_CHECKING:
    from app.models.ai_conversations import AIConversation
    from app.models.requests import Request
    from app.models.students import Student


class Department(BaseModel, Base):
    """University department / routing target (DATABASE_DESIGN.md §14)."""

    __tablename__ = "departments"

    code: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    email: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    building: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    office_hours: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    head_name: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    agent_key: Mapped[AgentKey | None] = mapped_column(AGENT_KEY, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    sort_order: Mapped[int] = mapped_column(
        sa.SmallInteger, nullable=False, server_default=sa.text("0")
    )

    __table_args__ = (
        sa.Index("ix_departments_code_key", "code", unique=True),
        sa.Index("ix_departments_name_key", "name", unique=True),
    )

    students: Mapped[list[Student]] = relationship(overlaps="department")
    conversations: Mapped[list[AIConversation]] = relationship(overlaps="department")
    requests: Mapped[list[Request]] = relationship(overlaps="department")

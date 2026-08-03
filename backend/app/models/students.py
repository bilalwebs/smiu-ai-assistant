"""``students`` model (DATABASE_DESIGN.md §13).

Identity & Access: academic profile for student-role users (PROJECT_RULES.md
``students`` table). A row exists only when the user's role is ``student``.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import BaseModel
from app.models.enums import STUDENT_STATUS, StudentStatus

if TYPE_CHECKING:
    from app.models.departments import Department
    from app.models.users import User


class Student(BaseModel, Base):
    """Academic profile, 1:1 with a student-role ``User`` (DATABASE_DESIGN.md §13)."""

    __tablename__ = "students"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    enrollment_no: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    program_name: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    program_level: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    admission_year: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    batch_year: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    current_semester: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    section: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    cgpa: Mapped[float | None] = mapped_column(sa.Numeric(3, 2), nullable=True)
    credit_hours_completed: Mapped[int | None] = mapped_column(
        sa.SmallInteger, nullable=True
    )
    status: Mapped[StudentStatus] = mapped_column(
        STUDENT_STATUS, nullable=False, server_default=sa.text("'active'")
    )
    cnic: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    nationality: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    guardian_relation: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)

    __table_args__ = (
        sa.Index("ix_students_user_id_key", "user_id", unique=True),
        sa.Index("ix_students_enrollment_no_key", "enrollment_no", unique=True),
        sa.Index("ix_students_department_id", "department_id"),
        sa.CheckConstraint(
            "cgpa IS NULL OR (cgpa >= 0.00 AND cgpa <= 4.00)",
            name="cgpa_check",
        ),
        sa.CheckConstraint(
            "current_semester IS NULL OR (current_semester >= 1 AND current_semester <= 16)",
            name="semester_check",
        ),
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id], overlaps="student")
    department: Mapped[Department | None] = relationship(
        foreign_keys=[department_id], overlaps="students"
    )

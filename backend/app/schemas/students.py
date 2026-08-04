"""Student schemas (API_SPECIFICATION.md §15).

Purpose:
    Define the authenticated student's academic profile, its editable fields,
    and the dashboard aggregates.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.models import StudentStatus
from app.schemas.base import ApiModel, UtcDateTime


class StudentRead(ApiModel):
    """Student academic profile, 1:1 with a student-role user (§13 of DATABASE_DESIGN.md)."""

    id: uuid.UUID
    user_id: uuid.UUID
    enrollment_no: str
    department_id: uuid.UUID | None = None
    program_name: str | None = None
    program_level: str | None = None
    admission_year: int | None = None
    batch_year: int | None = None
    current_semester: int | None = None
    section: str | None = None
    cgpa: float | None = None
    credit_hours_completed: int | None = None
    status: StudentStatus
    cnic: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    nationality: str | None = None
    address: str | None = None
    phone: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_relation: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class StudentUpdate(BaseModel):
    """Editable academic profile fields for ``PATCH /students/me``."""

    program_name: str | None = Field(default=None, max_length=150)
    program_level: str | None = Field(default=None, max_length=30)
    admission_year: int | None = Field(default=None, ge=1900, le=2100)
    batch_year: int | None = Field(default=None, ge=1900, le=2100)
    current_semester: int | None = Field(default=None, ge=1, le=16)
    section: str | None = Field(default=None, max_length=10)
    cgpa: float | None = Field(default=None, ge=0.0, le=4.0)
    credit_hours_completed: int | None = Field(default=None, ge=0)
    cnic: str | None = Field(default=None, max_length=20)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    nationality: str | None = Field(default=None, max_length=50)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    guardian_name: str | None = Field(default=None, max_length=150)
    guardian_phone: str | None = Field(default=None, max_length=30)
    guardian_relation: str | None = Field(default=None, max_length=30)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)


class StudentDashboardRead(ApiModel):
    """Dashboard aggregates for ``GET /students/me/dashboard``.

    Counts are owner-scoped: ``active_requests`` covers in-flight statuses
    (submitted/in_review/assigned/processing), ``pending_requests`` covers
    drafts awaiting submission, ``resolved_requests`` covers resolved/closed.
    """

    active_requests: int
    pending_requests: int
    resolved_requests: int
    unread_notifications: int

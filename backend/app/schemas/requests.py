"""Request schemas (API_SPECIFICATION.md §18).

Purpose:
    Define the workflow-request payloads: creation, editable fields, status
    transitions, and the read representation. The status machine itself is
    enforced by :class:`app.services.requests.RequestService`.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.models import (
    RequestPriority,
    RequestSource,
    RequestStatus,
    RequestType,
)
from app.schemas.base import ApiModel, UtcDateTime


class RequestCreate(BaseModel):
    """Payload for ``POST /requests`` (draft or submitted, §18)."""

    request_type: RequestType
    title: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    department_id: uuid.UUID | None = None
    description: str | None = None
    priority: RequestPriority = RequestPriority.MEDIUM
    source: RequestSource = RequestSource.MANUAL
    status: RequestStatus = RequestStatus.DRAFT


class RequestUpdate(BaseModel):
    """Editable request fields for ``PATCH /requests/{id}``."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=50)
    priority: RequestPriority | None = None
    department_id: uuid.UUID | None = None
    due_date: date | None = None


class RequestStatusUpdate(BaseModel):
    """Payload for explicit status transitions (§18)."""

    status: RequestStatus
    resolution_notes: str | None = None
    rejection_reason: str | None = None


class RequestRead(ApiModel):
    """Workflow request representation (DATABASE_DESIGN.md §17)."""

    id: uuid.UUID
    request_no: str
    user_id: uuid.UUID
    department_id: uuid.UUID | None = None
    request_type: RequestType
    category: str | None = None
    priority: RequestPriority
    status: RequestStatus
    title: str
    description: str | None = None
    source: RequestSource
    conversation_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    due_date: date | None = None
    resolution_notes: str | None = None
    resolved_at: UtcDateTime | None = None
    closed_at: UtcDateTime | None = None
    rejected_at: UtcDateTime | None = None
    rejection_reason: str | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime

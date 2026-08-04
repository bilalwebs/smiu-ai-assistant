"""``requests`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import RequestStatus, RequestType
from app.services import RequestService
from app.services.exceptions import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)


async def test_create_request_happy_path_defaults_to_draft(
    request_service, user_factory
) -> None:
    user = await user_factory()
    req = await request_service.create_request(
        user_id=user.id,
        request_type=RequestType.GENERAL,
        title="Need a transcript",
    )
    assert req.user_id == user.id
    assert req.request_type == RequestType.GENERAL
    assert req.status == RequestStatus.DRAFT
    assert req.request_no.startswith("REQ-")


async def test_create_request_explicit_submitted(request_service, user_factory) -> None:
    user = await user_factory()
    req = await request_service.create_request(
        user_id=user.id,
        request_type=RequestType.ADMISSION,
        title="Admission question",
        status=RequestStatus.SUBMITTED,
    )
    assert req.status == RequestStatus.SUBMITTED


async def test_create_request_missing_user_raises(
    request_service: RequestService,
) -> None:
    with pytest.raises(NotFoundError):
        await request_service.create_request(
            user_id=uuid.uuid4(), request_type=RequestType.GENERAL, title="Hello"
        )


async def test_create_request_missing_department_raises(
    request_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(NotFoundError):
        await request_service.create_request(
            user_id=user.id,
            request_type=RequestType.GENERAL,
            title="Hello",
            department_id=uuid.uuid4(),
        )


async def test_create_request_blank_title_raises(request_service, user_factory) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await request_service.create_request(
            user_id=user.id, request_type=RequestType.GENERAL, title="  "
        )


async def test_create_request_invalid_initial_status_raises(
    request_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await request_service.create_request(
            user_id=user.id,
            request_type=RequestType.GENERAL,
            title="Hello",
            status=RequestStatus.RESOLVED,
        )


async def test_create_request_duplicate_number_raises(
    request_service, user_factory
) -> None:
    user = await user_factory()
    await request_service.create_request(
        user_id=user.id, request_type=RequestType.GENERAL, title="A", request_no="REQ-1"
    )
    with pytest.raises(ConflictError):
        await request_service.create_request(
            user_id=user.id,
            request_type=RequestType.GENERAL,
            title="B",
            request_no="REQ-1",
        )


async def test_assign_request_happy_path(request_service, user_factory) -> None:
    owner = await user_factory()
    assignee = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id,
        request_type=RequestType.EXAMINATION,
        title="Exam query",
        status=RequestStatus.SUBMITTED,
    )
    assigned = await request_service.assign_request(
        request_id=req.id, assigned_to=assignee.id
    )
    assert assigned.status == RequestStatus.ASSIGNED
    assert assigned.assigned_to == assignee.id


async def test_assign_request_from_draft_raises(request_service, user_factory) -> None:
    owner = await user_factory()
    assignee = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id, request_type=RequestType.GENERAL, title="Draft"
    )
    with pytest.raises(InvalidStateError):
        await request_service.assign_request(
            request_id=req.id, assigned_to=assignee.id
        )


async def test_assign_request_missing_assignee_raises(
    request_service, user_factory
) -> None:
    owner = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id,
        request_type=RequestType.GENERAL,
        title="Hello",
        status=RequestStatus.SUBMITTED,
    )
    with pytest.raises(NotFoundError):
        await request_service.assign_request(
            request_id=req.id, assigned_to=uuid.uuid4()
        )


async def test_assign_request_missing_request_raises(
    request_service, user_factory
) -> None:
    assignee = await user_factory()
    with pytest.raises(NotFoundError):
        await request_service.assign_request(
            request_id=uuid.uuid4(), assigned_to=assignee.id
        )


async def test_resolve_request_sets_resolved_at(request_service, user_factory) -> None:
    owner = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id,
        request_type=RequestType.GENERAL,
        title="Hello",
        status=RequestStatus.SUBMITTED,
    )
    resolved = await request_service.resolve_request(
        request_id=req.id, resolution_notes="Done"
    )
    assert resolved.status == RequestStatus.RESOLVED
    assert resolved.resolved_at is not None
    assert resolved.resolution_notes == "Done"


async def test_resolve_request_from_draft_raises(request_service, user_factory) -> None:
    owner = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id, request_type=RequestType.GENERAL, title="Draft"
    )
    with pytest.raises(InvalidStateError):
        await request_service.resolve_request(request_id=req.id)


async def test_reject_request_requires_reason(request_service, user_factory) -> None:
    owner = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id,
        request_type=RequestType.GENERAL,
        title="Hello",
        status=RequestStatus.SUBMITTED,
    )
    with pytest.raises(ValidationError):
        await request_service.reject_request(request_id=req.id, rejection_reason="  ")


async def test_reject_request_happy_path(request_service, user_factory) -> None:
    owner = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id,
        request_type=RequestType.GENERAL,
        title="Hello",
        status=RequestStatus.SUBMITTED,
    )
    rejected = await request_service.reject_request(
        request_id=req.id, rejection_reason="Incomplete documents"
    )
    assert rejected.status == RequestStatus.REJECTED
    assert rejected.rejected_at is not None
    assert rejected.rejection_reason == "Incomplete documents"


async def test_terminal_states_are_absorbing(request_service, user_factory) -> None:
    owner = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id,
        request_type=RequestType.GENERAL,
        title="Hello",
        status=RequestStatus.SUBMITTED,
    )
    await request_service.resolve_request(request_id=req.id)
    with pytest.raises(InvalidStateError):
        await request_service.reject_request(
            request_id=req.id, rejection_reason="Too late"
        )
    await request_service.change_status(request_id=req.id, status=RequestStatus.CLOSED)
    with pytest.raises(InvalidStateError):
        await request_service.change_status(
            request_id=req.id, status=RequestStatus.PROCESSING
        )


async def test_change_status_same_status_raises(request_service, user_factory) -> None:
    owner = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id,
        request_type=RequestType.GENERAL,
        title="Hello",
        status=RequestStatus.SUBMITTED,
    )
    with pytest.raises(InvalidStateError):
        await request_service.change_status(
            request_id=req.id, status=RequestStatus.SUBMITTED
        )


async def test_change_status_to_closed_sets_closed_at(
    request_service, user_factory
) -> None:
    owner = await user_factory()
    req = await request_service.create_request(
        user_id=owner.id,
        request_type=RequestType.GENERAL,
        title="Hello",
        status=RequestStatus.SUBMITTED,
    )
    await request_service.resolve_request(request_id=req.id)
    closed = await request_service.change_status(
        request_id=req.id, status=RequestStatus.CLOSED
    )
    assert closed.status == RequestStatus.CLOSED
    assert closed.closed_at is not None


async def test_resolve_missing_request_raises(request_service: RequestService) -> None:
    with pytest.raises(NotFoundError):
        await request_service.resolve_request(request_id=uuid.uuid4())

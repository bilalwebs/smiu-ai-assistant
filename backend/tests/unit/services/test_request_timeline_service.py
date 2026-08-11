"""``request_timeline`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import RequestStatus, RequestType
from app.services import RequestTimelineService
from app.services.exceptions import NotFoundError, ValidationError


async def test_add_event_happy_path(
    request_timeline_service, request_service, user_factory
) -> None:
    user = await user_factory()
    req = await request_service.create_request(
        user_id=user.id,
        request_type=RequestType.GENERAL,
        title="Hello",
        status=RequestStatus.SUBMITTED,
    )
    event = await request_timeline_service.add_event(
        request_id=req.id,
        to_status=RequestStatus.IN_REVIEW,
        from_status=RequestStatus.SUBMITTED,
        action="review.start",
        actor_user_id=user.id,
    )
    assert event.request_id == req.id
    assert event.from_status == RequestStatus.SUBMITTED
    assert event.to_status == RequestStatus.IN_REVIEW
    assert event.action == "review.start"
    assert event.actor_user_id == user.id


async def test_add_event_initial_transition_has_no_from_status(
    request_timeline_service, request_service, user_factory
) -> None:
    user = await user_factory()
    req = await request_service.create_request(
        user_id=user.id, request_type=RequestType.GENERAL, title="Hello"
    )
    event = await request_timeline_service.add_event(
        request_id=req.id, to_status=RequestStatus.DRAFT, action="request.create"
    )
    assert event.from_status is None
    assert event.to_status == RequestStatus.DRAFT


async def test_add_event_missing_request_raises(
    request_timeline_service: RequestTimelineService,
) -> None:
    with pytest.raises(NotFoundError):
        await request_timeline_service.add_event(
            request_id=uuid.uuid4(),
            to_status=RequestStatus.IN_REVIEW,
            action="review.start",
        )


async def test_add_event_missing_actor_raises(
    request_timeline_service, request_service, user_factory
) -> None:
    user = await user_factory()
    req = await request_service.create_request(
        user_id=user.id, request_type=RequestType.GENERAL, title="Hello"
    )
    with pytest.raises(NotFoundError):
        await request_timeline_service.add_event(
            request_id=req.id,
            to_status=RequestStatus.IN_REVIEW,
            action="review.start",
            actor_user_id=uuid.uuid4(),
        )


async def test_add_event_blank_action_raises(
    request_timeline_service, request_service, user_factory
) -> None:
    user = await user_factory()
    req = await request_service.create_request(
        user_id=user.id, request_type=RequestType.GENERAL, title="Hello"
    )
    with pytest.raises(ValidationError):
        await request_timeline_service.add_event(
            request_id=req.id, to_status=RequestStatus.IN_REVIEW, action="  "
        )


async def test_add_event_invalid_status_raises(
    request_timeline_service, request_service, user_factory
) -> None:
    user = await user_factory()
    req = await request_service.create_request(
        user_id=user.id, request_type=RequestType.GENERAL, title="Hello"
    )
    with pytest.raises(ValidationError):
        await request_timeline_service.add_event(
            request_id=req.id, to_status="not-a-status", action="x"
        )


async def test_get_events_returns_chronological_order(
    request_timeline_service, request_service, user_factory
) -> None:
    user = await user_factory()
    req = await request_service.create_request(
        user_id=user.id,
        request_type=RequestType.GENERAL,
        title="Hello",
        status=RequestStatus.SUBMITTED,
    )
    first = await request_timeline_service.add_event(
        request_id=req.id,
        to_status=RequestStatus.IN_REVIEW,
        from_status=RequestStatus.SUBMITTED,
        action="review.start",
    )
    second = await request_timeline_service.add_event(
        request_id=req.id,
        to_status=RequestStatus.ASSIGNED,
        from_status=RequestStatus.IN_REVIEW,
        action="assign",
    )
    events = await request_timeline_service.get_events(request_id=req.id)
    assert len(events) == 3
    assert events[0].action == "created"
    assert [event.id for event in events[1:]] == [first.id, second.id]


async def test_get_events_missing_request_raises(
    request_timeline_service: RequestTimelineService,
) -> None:
    with pytest.raises(NotFoundError):
        await request_timeline_service.get_events(request_id=uuid.uuid4())

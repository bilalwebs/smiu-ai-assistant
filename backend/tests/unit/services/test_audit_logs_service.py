"""``audit_logs`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.services import AuditLogService
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.time import utc_now


async def test_create_log_happy_path(audit_log_service, user_factory) -> None:
    user = await user_factory()
    log = await audit_log_service.create_log(
        action="request.soft_delete",
        resource_type="Request",
        resource_id=str(uuid.uuid4()),
        actor_user_id=user.id,
        new_values={"status": "deleted"},
        correlation_id="corr-123",
    )
    assert log.action == "request.soft_delete"
    assert log.resource_type == "Request"
    assert log.actor_user_id == user.id
    assert log.new_values == {"status": "deleted"}
    assert log.correlation_id == "corr-123"


async def test_create_log_without_actor(audit_log_service: AuditLogService) -> None:
    log = await audit_log_service.create_log(
        action="system.boot", resource_type="System"
    )
    assert log.actor_user_id is None


async def test_create_log_blank_action_raises(
    audit_log_service: AuditLogService,
) -> None:
    with pytest.raises(ValidationError):
        await audit_log_service.create_log(action="  ", resource_type="System")


async def test_create_log_blank_resource_type_raises(
    audit_log_service: AuditLogService,
) -> None:
    with pytest.raises(ValidationError):
        await audit_log_service.create_log(action="system.boot", resource_type="  ")


async def test_create_log_action_too_long_raises(
    audit_log_service: AuditLogService,
) -> None:
    with pytest.raises(ValidationError):
        await audit_log_service.create_log(
            action="x" * 101, resource_type="System"
        )


async def test_create_log_resource_type_too_long_raises(
    audit_log_service: AuditLogService,
) -> None:
    with pytest.raises(ValidationError):
        await audit_log_service.create_log(
            action="system.boot", resource_type="y" * 101
        )


async def test_create_log_resource_id_too_long_raises(
    audit_log_service: AuditLogService,
) -> None:
    with pytest.raises(ValidationError):
        await audit_log_service.create_log(
            action="system.boot",
            resource_type="System",
            resource_id="z" * 101,
        )


async def test_create_log_correlation_id_too_long_raises(
    audit_log_service: AuditLogService,
) -> None:
    with pytest.raises(ValidationError):
        await audit_log_service.create_log(
            action="system.boot",
            resource_type="System",
            correlation_id="w" * 101,
        )


async def test_create_log_missing_actor_raises(
    audit_log_service: AuditLogService,
) -> None:
    with pytest.raises(NotFoundError):
        await audit_log_service.create_log(
            action="request.delete",
            resource_type="Request",
            actor_user_id=uuid.uuid4(),
        )


async def test_list_by_actor_returns_newest_first(
    audit_log_service, user_factory, db_session
) -> None:
    user = await user_factory()
    first = await audit_log_service.create_log(
        action="a.first", resource_type="Request", actor_user_id=user.id
    )
    second = await audit_log_service.create_log(
        action="a.second", resource_type="Request", actor_user_id=user.id
    )
    # ``created_at`` has second precision on SQLite, so pin explicit timestamps
    # to make the newest-first ordering deterministic.
    now = utc_now()
    first.created_at = now - timedelta(minutes=5)
    second.created_at = now
    await db_session.flush()
    logs = await audit_log_service.list_by_actor(actor_user_id=user.id)
    assert [log.action for log in logs] == ["a.second", "a.first"]


async def test_list_by_actor_excludes_other_actors(
    audit_log_service, user_factory
) -> None:
    actor = await user_factory()
    other = await user_factory()
    await audit_log_service.create_log(
        action="mine", resource_type="Request", actor_user_id=actor.id
    )
    await audit_log_service.create_log(
        action="theirs", resource_type="Request", actor_user_id=other.id
    )
    logs = await audit_log_service.list_by_actor(actor_user_id=actor.id)
    assert [log.action for log in logs] == ["mine"]


async def test_list_by_actor_missing_user_raises(
    audit_log_service: AuditLogService,
) -> None:
    with pytest.raises(NotFoundError):
        await audit_log_service.list_by_actor(actor_user_id=uuid.uuid4())


async def test_list_by_resource_filters_by_resource(
    audit_log_service, user_factory
) -> None:
    user = await user_factory()
    resource_id = str(uuid.uuid4())
    await audit_log_service.create_log(
        action="update", resource_type="Request", resource_id=resource_id,
        actor_user_id=user.id,
    )
    await audit_log_service.create_log(
        action="delete", resource_type="Request", resource_id=str(uuid.uuid4()),
        actor_user_id=user.id,
    )
    logs = await audit_log_service.list_by_resource(
        resource_type="Request", resource_id=resource_id
    )
    assert [log.action for log in logs] == ["update"]


async def test_list_by_resource_blank_type_raises(
    audit_log_service: AuditLogService,
) -> None:
    with pytest.raises(ValidationError):
        await audit_log_service.list_by_resource(resource_type="  ")

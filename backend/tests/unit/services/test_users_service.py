"""``users`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import UserStatus
from app.repositories import UserRepository
from app.services import UserService
from app.services.exceptions import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)


async def test_create_user_happy_path(user_service: UserService) -> None:
    user = await user_service.create_user(
        email="student@example.com", password_hash="hashed", full_name="Ali Khan"
    )
    assert user.email == "student@example.com"
    assert user.full_name == "Ali Khan"
    assert user.role.value == "student"
    assert user.status == UserStatus.PENDING
    assert user.id is not None


async def test_create_user_normalizes_email_lowercase(user_service: UserService) -> None:
    user = await user_service.create_user(
        email="  Student@Example.COM ", password_hash="h", full_name="Ali"
    )
    assert user.email == "student@example.com"


async def test_create_user_duplicate_email_raises_conflict(
    user_service, user_factory
) -> None:
    existing = await user_factory()
    with pytest.raises(ConflictError):
        await user_service.create_user(
            email=existing.email, password_hash="h", full_name="Other"
        )


async def test_create_user_blank_fields_raise_validation(
    user_service: UserService,
) -> None:
    with pytest.raises(ValidationError):
        await user_service.create_user(email="a@b.com", password_hash="h", full_name="   ")
    with pytest.raises(ValidationError):
        await user_service.create_user(email="", password_hash="h", full_name="Ali")


async def test_update_user_updates_profile(user_service, user_factory) -> None:
    user = await user_factory(full_name="Before")
    updated = await user_service.update_user(user.id, full_name="After")
    assert updated.full_name == "After"
    assert updated.id == user.id


async def test_update_user_missing_raises_not_found(user_service: UserService) -> None:
    with pytest.raises(NotFoundError):
        await user_service.update_user(uuid.uuid4(), full_name="Ghost")


async def test_update_user_email_conflict_raises(user_service, user_factory) -> None:
    first = await user_factory()
    second = await user_factory()
    with pytest.raises(ConflictError):
        await user_service.update_user(second.id, email=first.email)


async def test_update_user_same_email_allowed(user_service, user_factory) -> None:
    user = await user_factory(email="same@example.com")
    updated = await user_service.update_user(user.id, email="same@example.com")
    assert updated.email == "same@example.com"


async def test_activate_user_transitions_to_active(user_service, user_factory) -> None:
    user = await user_factory(status=UserStatus.PENDING)
    activated = await user_service.activate_user(user.id)
    assert activated.status == UserStatus.ACTIVE


async def test_activate_user_already_active_raises(user_service, user_factory) -> None:
    user = await user_factory(status=UserStatus.ACTIVE)
    with pytest.raises(InvalidStateError):
        await user_service.activate_user(user.id)


async def test_deactivate_user_transitions(user_service, user_factory) -> None:
    user = await user_factory(status=UserStatus.ACTIVE)
    deactivated = await user_service.deactivate_user(user.id)
    assert deactivated.status == UserStatus.DEACTIVATED


async def test_deactivate_user_already_deactivated_raises(
    user_service, user_factory
) -> None:
    user = await user_factory(status=UserStatus.DEACTIVATED)
    with pytest.raises(InvalidStateError):
        await user_service.deactivate_user(user.id)


async def test_activate_missing_user_raises_not_found(user_service: UserService) -> None:
    with pytest.raises(NotFoundError):
        await user_service.activate_user(uuid.uuid4())


async def test_create_user_commit_persists(db_engine, user_service: UserService) -> None:
    created = await user_service.create_user(
        email="committed@example.com", password_hash="h", full_name="Committed"
    )
    await user_service.commit()
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with factory() as session:
        repo = UserRepository(session)
        found = await repo.get_by_email("committed@example.com")
        assert found is not None
        assert found.id == created.id


async def test_create_user_rollback_discards(
    db_session, user_service: UserService
) -> None:
    await user_service.create_user(
        email="rolled@example.com", password_hash="h", full_name="Rolled"
    )
    await user_service.rollback()
    repo = UserRepository(db_session)
    assert await repo.get_by_email("rolled@example.com") is None

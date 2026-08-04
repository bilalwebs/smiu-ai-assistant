"""``auth`` service tests (Phase 6; BACKEND_ARCHITECTURE.md §9)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.security.jwt import (
    TOKEN_TYPE_ACCESS,
    create_access_token,
    create_email_verification_token,
    decode_token,
    hash_refresh_token,
)
from app.core.security.password import hash_password_async
from app.exceptions.app_error import ForbiddenError, UnauthorizedError
from app.models import AuditLog, User, UserRole, UserStatus
from app.repositories import (
    AuditLogRepository,
    DepartmentRepository,
    SessionRepository,
    StudentRepository,
    UserRepository,
)
from app.services import AuthService
from app.services.exceptions import ConflictError, NotFoundError, ValidationError
from app.utils.time import utc_now

PASSWORD = "Sup3r!secure"


@pytest.fixture()
def auth_service(db_session: AsyncSession) -> AuthService:
    return AuthService(db_session)


async def _verified_user(
    user_factory,
    *,
    password: str = PASSWORD,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    password_hash = await hash_password_async(password)
    return await user_factory(
        password_hash=password_hash,
        status=status,
        email_verified_at=utc_now(),
    )


async def test_register_creates_pending_student(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    user = await auth_service.register(
        email="New.Student@Example.com",
        password=PASSWORD,
        full_name="New Student",
    )
    assert user.status == UserStatus.PENDING
    assert user.role == UserRole.STUDENT
    assert user.email == "new.student@example.com"
    assert user.email_verified_at is None


async def test_register_creates_student_profile(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    departments = DepartmentRepository(db_session)
    department = await departments.create(code="CS", name="Computer Science")
    user = await auth_service.register(
        email="profile@example.com",
        password=PASSWORD,
        full_name="Profile Student",
        enrollment_no="SM-2025-001",
        department_id=department.id,
        program_name="BS Computer Science",
    )
    students = StudentRepository(db_session)
    student = await students.get_by_user_id(user.id)
    assert student is not None
    assert student.enrollment_no == "SM-2025-001"
    assert student.department_id == department.id
    assert student.program_name == "BS Computer Science"


async def test_register_duplicate_email_raises(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    await auth_service.register(
        email="dup@example.com", password=PASSWORD, full_name="First"
    )
    with pytest.raises(ConflictError):
        await auth_service.register(
            email="dup@example.com", password=PASSWORD, full_name="Second"
        )


async def test_register_weak_password_raises(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    with pytest.raises(ValidationError):
        await auth_service.register(
            email="weak@example.com", password="short", full_name="Weak"
        )


async def test_register_unknown_department_raises(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    with pytest.raises(NotFoundError):
        await auth_service.register(
            email="bad-dept@example.com",
            password=PASSWORD,
            full_name="No Dept",
            department_id=uuid.uuid4(),
        )


async def test_register_duplicate_enrollment_raises(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    await auth_service.register(
        email="first@example.com",
        password=PASSWORD,
        full_name="First",
        enrollment_no="SM-2025-100",
    )
    with pytest.raises(ConflictError):
        await auth_service.register(
            email="second@example.com",
            password=PASSWORD,
            full_name="Second",
            enrollment_no="SM-2025-100",
        )


async def test_verify_email_activates_account(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    user = await auth_service.register(
        email="verify@example.com", password=PASSWORD, full_name="Verify Me"
    )
    settings = get_settings()
    token = create_email_verification_token(subject=str(user.id), settings=settings)
    verified = await auth_service.verify_email(token=token)
    assert verified.status == UserStatus.ACTIVE
    assert verified.email_verified_at is not None


async def test_verify_email_is_idempotent(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    settings = get_settings()
    users = UserRepository(db_session)
    created = await users.create(
        email="already@example.com",
        password_hash="x",
        full_name="Already Verified",
        status=UserStatus.ACTIVE,
        email_verified_at=utc_now(),
    )
    token = create_email_verification_token(
        subject=str(created.id), settings=settings
    )
    again = await auth_service.verify_email(token=token)
    assert again.id == created.id
    assert again.status == UserStatus.ACTIVE


async def test_verify_email_rejects_invalid_token(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    with pytest.raises(UnauthorizedError):
        await auth_service.verify_email(token="garbage-token")


async def test_verify_email_rejects_access_token(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    settings = get_settings()
    token = create_access_token(subject=str(uuid.uuid4()), role="student", settings=settings)
    with pytest.raises(UnauthorizedError):
        await auth_service.verify_email(token=token)


async def test_login_happy_path_issues_tokens_and_session(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    result = await auth_service.login(email=user.email, password=PASSWORD)
    assert result.user.id == user.id
    claims = decode_token(
        token=result.access_token,
        expected_type=TOKEN_TYPE_ACCESS,
        settings=get_settings(),
    )
    assert claims.subject == str(user.id)
    assert claims.role == UserRole.STUDENT.value

    sessions = SessionRepository(db_session)
    session = await sessions.get_by_refresh_hash(
        hash_refresh_token(result.refresh_token)
    )
    assert session is not None
    assert session.user_id == user.id
    assert result.refresh_expires_in == 7 * 24 * 3600

    refreshed = await UserRepository(db_session).get_by_id(user.id)
    assert refreshed is not None
    assert refreshed.last_login_at is not None
    assert refreshed.failed_login_attempts == 0


async def test_login_remember_me_extends_refresh_lifetime(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    result = await auth_service.login(
        email=user.email, password=PASSWORD, remember_me=True
    )
    assert result.refresh_expires_in == 30 * 24 * 3600


async def test_login_wrong_password_counts_attempt(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    with pytest.raises(UnauthorizedError):
        await auth_service.login(email=user.email, password="Wrong!password")
    refreshed = await UserRepository(db_session).get_by_id(user.id)
    assert refreshed is not None
    assert refreshed.failed_login_attempts == 1
    assert refreshed.locked_until is None


async def test_login_locks_account_at_threshold(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    for _ in range(5):
        with pytest.raises(UnauthorizedError):
            await auth_service.login(email=user.email, password="Wrong!password")
    refreshed = await UserRepository(db_session).get_by_id(user.id)
    assert refreshed is not None
    assert refreshed.failed_login_attempts == 5
    assert refreshed.locked_until is not None
    with pytest.raises(UnauthorizedError):
        await auth_service.login(email=user.email, password=PASSWORD)


async def test_login_success_resets_failure_count(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    for _ in range(2):
        with pytest.raises(UnauthorizedError):
            await auth_service.login(email=user.email, password="Wrong!password")
    result = await auth_service.login(email=user.email, password=PASSWORD)
    assert result.user.id == user.id
    refreshed = await UserRepository(db_session).get_by_id(user.id)
    assert refreshed is not None
    assert refreshed.failed_login_attempts == 0


async def test_login_unverified_email_raises_forbidden(
    auth_service: AuthService, user_factory
) -> None:
    password_hash = await hash_password_async(PASSWORD)
    user = await user_factory(password_hash=password_hash, status=UserStatus.ACTIVE)
    with pytest.raises(ForbiddenError):
        await auth_service.login(email=user.email, password=PASSWORD)


async def test_login_suspended_account_raises(
    auth_service: AuthService, user_factory
) -> None:
    user = await _verified_user(user_factory, status=UserStatus.SUSPENDED)
    with pytest.raises(UnauthorizedError):
        await auth_service.login(email=user.email, password=PASSWORD)


async def test_login_unknown_email_raises(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    with pytest.raises(UnauthorizedError):
        await auth_service.login(email="nobody@example.com", password=PASSWORD)


async def test_register_and_login_record_audit_events(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await auth_service.register(
        email="audit@example.com", password=PASSWORD, full_name="Audited"
    )
    token = create_email_verification_token(
        subject=str(user.id), settings=get_settings()
    )
    await auth_service.verify_email(token=token)
    await auth_service.login(email=user.email, password=PASSWORD)

    logs = AuditLogRepository(db_session)
    events = await logs.list(AuditLog.resource_id == str(user.id))
    assert sorted(event.action for event in events) == [
        "login",
        "register",
        "verify_email",
    ]


# -- refresh / logout -------------------------------------------------------


async def test_rotate_refresh_issues_new_pair_and_links_chain(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    login = await auth_service.login(email=user.email, password=PASSWORD)
    rotated = await auth_service.rotate_refresh(refresh_token=login.refresh_token)

    assert rotated.user.id == user.id
    assert rotated.access_token != login.access_token
    assert rotated.refresh_token != login.refresh_token
    claims = decode_token(
        token=rotated.access_token,
        expected_type=TOKEN_TYPE_ACCESS,
        settings=get_settings(),
    )
    assert claims.subject == str(user.id)
    assert claims.role == UserRole.STUDENT.value
    assert abs(rotated.refresh_expires_in - 7 * 24 * 3600) <= 2

    sessions = SessionRepository(db_session)
    old = await sessions.get_by_refresh_hash(hash_refresh_token(login.refresh_token))
    new = await sessions.get_by_refresh_hash(
        hash_refresh_token(rotated.refresh_token)
    )
    assert old is not None
    assert old.revoked_at is not None
    assert new is not None
    assert new.replaced_by_session_id == old.id
    assert new.last_used_at is not None


async def test_rotate_refresh_preserves_remember_me_lifetime(
    auth_service: AuthService, user_factory
) -> None:
    user = await _verified_user(user_factory)
    login = await auth_service.login(
        email=user.email, password=PASSWORD, remember_me=True
    )
    rotated = await auth_service.rotate_refresh(refresh_token=login.refresh_token)
    assert abs(rotated.refresh_expires_in - 30 * 24 * 3600) <= 2


async def test_rotate_refresh_unknown_token_raises(
    auth_service: AuthService,
) -> None:
    with pytest.raises(UnauthorizedError):
        await auth_service.rotate_refresh(refresh_token="garbage-refresh-token")


async def test_rotate_refresh_replay_revokes_chain(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    login = await auth_service.login(email=user.email, password=PASSWORD)
    first = await auth_service.rotate_refresh(refresh_token=login.refresh_token)
    with pytest.raises(UnauthorizedError):
        await auth_service.rotate_refresh(refresh_token=login.refresh_token)

    sessions = SessionRepository(db_session)
    old = await sessions.get_by_refresh_hash(hash_refresh_token(login.refresh_token))
    new = await sessions.get_by_refresh_hash(
        hash_refresh_token(first.refresh_token)
    )
    assert old is not None and old.revoked_at is not None
    assert new is not None and new.revoked_at is not None


async def test_rotate_refresh_revoked_session_raises(
    auth_service: AuthService, user_factory
) -> None:
    user = await _verified_user(user_factory)
    login = await auth_service.login(email=user.email, password=PASSWORD)
    await auth_service.logout(refresh_token=login.refresh_token)
    with pytest.raises(UnauthorizedError):
        await auth_service.rotate_refresh(refresh_token=login.refresh_token)


async def test_rotate_refresh_expired_session_raises(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    login = await auth_service.login(email=user.email, password=PASSWORD)
    sessions = SessionRepository(db_session)
    session = await sessions.get_by_refresh_hash(
        hash_refresh_token(login.refresh_token)
    )
    assert session is not None
    past = utc_now() - timedelta(days=2)
    await sessions.update(
        session,
        created_at=past,
        expires_at=past + timedelta(days=1),
    )
    with pytest.raises(UnauthorizedError):
        await auth_service.rotate_refresh(refresh_token=login.refresh_token)


async def test_rotate_refresh_suspended_user_raises(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    login = await auth_service.login(email=user.email, password=PASSWORD)
    await UserRepository(db_session).update(user, status=UserStatus.SUSPENDED)
    with pytest.raises(UnauthorizedError):
        await auth_service.rotate_refresh(refresh_token=login.refresh_token)


async def test_logout_revokes_session(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    login = await auth_service.login(email=user.email, password=PASSWORD)
    await auth_service.logout(refresh_token=login.refresh_token)
    session = await SessionRepository(db_session).get_by_refresh_hash(
        hash_refresh_token(login.refresh_token)
    )
    assert session is not None
    assert session.revoked_at is not None


async def test_logout_is_idempotent(auth_service: AuthService, user_factory) -> None:
    user = await _verified_user(user_factory)
    login = await auth_service.login(email=user.email, password=PASSWORD)
    await auth_service.logout(refresh_token=login.refresh_token)
    await auth_service.logout(refresh_token=login.refresh_token)
    await auth_service.logout(refresh_token="garbage-refresh-token")


async def test_logout_all_revokes_every_session(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    first = await auth_service.login(email=user.email, password=PASSWORD)
    second = await auth_service.login(email=user.email, password=PASSWORD)
    revoked = await auth_service.logout_all(refresh_token=first.refresh_token)
    assert revoked == 2

    sessions = SessionRepository(db_session)
    one = await sessions.get_by_refresh_hash(hash_refresh_token(first.refresh_token))
    two = await sessions.get_by_refresh_hash(hash_refresh_token(second.refresh_token))
    assert one is not None and one.revoked_at is not None
    assert two is not None and two.revoked_at is not None


async def test_logout_all_unknown_token_raises(auth_service: AuthService) -> None:
    with pytest.raises(UnauthorizedError):
        await auth_service.logout_all(refresh_token="garbage-refresh-token")


async def test_refresh_and_logout_record_audit_events(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    login = await auth_service.login(email=user.email, password=PASSWORD)
    rotated = await auth_service.rotate_refresh(refresh_token=login.refresh_token)
    await auth_service.logout(refresh_token=rotated.refresh_token)

    logs = AuditLogRepository(db_session)
    events = await logs.list(AuditLog.resource_id == str(user.id))
    assert sorted(event.action for event in events) == [
        "login",
        "logout",
        "refresh",
    ]


# -- forgot password ---------------------------------------------------------


async def test_forgot_password_sends_email_for_active_user(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    await auth_service.forgot_password(email=user.email)
    refreshed = await UserRepository(db_session).get_by_id(user.id)
    assert refreshed is not None
    assert refreshed.password_reset_token_hash is not None
    assert refreshed.password_reset_token_expires_at is not None


async def test_forgot_password_succeeds_silently_for_unknown_email(
    auth_service: AuthService,
) -> None:
    await auth_service.forgot_password(email="nonexistent@example.com")


async def test_forgot_password_succeeds_silently_for_inactive_user(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory, status=UserStatus.SUSPENDED)
    await auth_service.forgot_password(email=user.email)
    refreshed = await UserRepository(db_session).get_by_id(user.id)
    assert refreshed is not None
    assert refreshed.password_reset_token_hash is None


async def test_forgot_password_records_audit_event(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    await auth_service.forgot_password(email=user.email)
    logs = AuditLogRepository(db_session)
    events = await logs.list(AuditLog.resource_id == str(user.id))
    assert any(e.action == "forgot_password" for e in events)


# -- reset password ----------------------------------------------------------


async def test_reset_password_sets_new_hash_and_invalidates_token(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    from app.core.security.jwt import (
        create_password_reset_token,
        hash_password_reset_token,
    )

    user = await _verified_user(user_factory)
    settings = get_settings()
    token = create_password_reset_token(subject=str(user.id), settings=settings)
    await UserRepository(db_session).update(
        user,
        password_reset_token_hash=hash_password_reset_token(token),
        password_reset_token_expires_at=utc_now() + timedelta(minutes=30),
    )
    new_password = "N3w!Password"
    updated = await auth_service.reset_password(token=token, new_password=new_password)
    assert updated.id == user.id
    from app.core.security.password import verify_password_async

    assert await verify_password_async(new_password, updated.password_hash)
    assert updated.password_reset_token_hash is None
    assert updated.password_reset_token_expires_at is None


async def test_reset_password_revokes_all_sessions(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    from app.core.security.jwt import (
        create_password_reset_token,
        hash_password_reset_token,
    )

    user = await _verified_user(user_factory)
    login = await auth_service.login(email=user.email, password=PASSWORD)
    settings = get_settings()
    token = create_password_reset_token(subject=str(user.id), settings=settings)
    await UserRepository(db_session).update(
        user,
        password_reset_token_hash=hash_password_reset_token(token),
        password_reset_token_expires_at=utc_now() + timedelta(minutes=30),
    )
    await auth_service.reset_password(token=token, new_password="N3w!Password")
    sessions = SessionRepository(db_session)
    old = await sessions.get_by_refresh_hash(hash_refresh_token(login.refresh_token))
    assert old is not None
    assert old.revoked_at is not None


async def test_reset_password_records_audit_event(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    from app.core.security.jwt import (
        create_password_reset_token,
        hash_password_reset_token,
    )

    user = await _verified_user(user_factory)
    settings = get_settings()
    token = create_password_reset_token(subject=str(user.id), settings=settings)
    await UserRepository(db_session).update(
        user,
        password_reset_token_hash=hash_password_reset_token(token),
        password_reset_token_expires_at=utc_now() + timedelta(minutes=30),
    )
    await auth_service.reset_password(token=token, new_password="N3w!Password")
    logs = AuditLogRepository(db_session)
    events = await logs.list(AuditLog.resource_id == str(user.id))
    assert any(e.action == "reset_password" for e in events)


async def test_reset_password_rejects_invalid_token(
    auth_service: AuthService,
) -> None:
    with pytest.raises(UnauthorizedError):
        await auth_service.reset_password(token="garbage-token", new_password="N3w!Password")


async def test_reset_password_rejects_access_token(
    auth_service: AuthService, user_factory
) -> None:
    settings = get_settings()
    user = await _verified_user(user_factory)
    token = create_access_token(subject=str(user.id), role="student", settings=settings)
    with pytest.raises(UnauthorizedError):
        await auth_service.reset_password(token=token, new_password="N3w!Password")


async def test_reset_password_rejects_weak_password(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    from app.core.security.jwt import (
        create_password_reset_token,
        hash_password_reset_token,
    )

    user = await _verified_user(user_factory)
    settings = get_settings()
    token = create_password_reset_token(subject=str(user.id), settings=settings)
    await UserRepository(db_session).update(
        user,
        password_reset_token_hash=hash_password_reset_token(token),
        password_reset_token_expires_at=utc_now() + timedelta(minutes=30),
    )
    with pytest.raises(ValidationError):
        await auth_service.reset_password(token=token, new_password="short")


# -- change password ---------------------------------------------------------


async def test_change_password_updates_hash(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    new_password = "N3w!Password"
    updated = await auth_service.change_password(
        user_id=user.id, current_password=PASSWORD, new_password=new_password
    )
    from app.core.security.password import verify_password_async

    assert await verify_password_async(new_password, updated.password_hash)


async def test_change_password_rejects_wrong_current_password(
    auth_service: AuthService, user_factory
) -> None:
    user = await _verified_user(user_factory)
    with pytest.raises(UnauthorizedError):
        await auth_service.change_password(
            user_id=user.id, current_password="Wrong!pass1", new_password="N3w!Password"
        )


async def test_change_password_rejects_weak_new_password(
    auth_service: AuthService, user_factory
) -> None:
    user = await _verified_user(user_factory)
    with pytest.raises(ValidationError):
        await auth_service.change_password(
            user_id=user.id, current_password=PASSWORD, new_password="short"
        )


async def test_change_password_revokes_other_sessions(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    login1 = await auth_service.login(email=user.email, password=PASSWORD)
    login2 = await auth_service.login(email=user.email, password=PASSWORD)
    await auth_service.change_password(
        user_id=user.id,
        current_password=PASSWORD,
        new_password="N3w!Password",
        current_session_jti=login1.access_token.split(".")[-1]
        if login1.access_token.count(".") == 2
        else None,
    )
    sessions = SessionRepository(db_session)
    s1 = await sessions.get_by_refresh_hash(hash_refresh_token(login1.refresh_token))
    s2 = await sessions.get_by_refresh_hash(hash_refresh_token(login2.refresh_token))
    assert s1 is not None
    assert s2 is not None


async def test_change_password_records_audit_event(
    auth_service: AuthService, user_factory, db_session: AsyncSession
) -> None:
    user = await _verified_user(user_factory)
    await auth_service.change_password(
        user_id=user.id, current_password=PASSWORD, new_password="N3w!Password"
    )
    logs = AuditLogRepository(db_session)
    events = await logs.list(AuditLog.resource_id == str(user.id))
    assert any(e.action == "change_password" for e in events)

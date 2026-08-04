"""Authentication service (Phase 6; BACKEND_ARCHITECTURE.md §9).

Purpose:
    Own the identity lifecycle: registration, email verification, and login
    with account lockout and remember-me sessions. Composes repositories and
    the audit/email services; the request-scoped DI session commits on success
    (BACKEND_ARCHITECTURE.md §12.3, §13), while the failed-login branch commits
    explicitly so the attempt counter and lock survive the request-level
    rollback that follows the raised ``401``.

Responsibilities:
    - Register a student account (pending), send a signed verification email.
    - Verify the signed email-verification token (idempotent).
    - Login: credential check, verification/status gates, lockout tracking,
      access + refresh token issuance, server-side session row.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.core.security.jwt import (
    TOKEN_TYPE_EMAIL_VERIFICATION,
    TOKEN_TYPE_PASSWORD_RESET,
    TokenClaims,
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_token,
    generate_jti,
    generate_refresh_token,
    hash_password_reset_token,
    hash_refresh_token,
)
from app.core.security.password import (
    hash_password_async,
    password_policy_errors,
    verify_password_async,
)
from app.exceptions.app_error import ForbiddenError, UnauthorizedError
from app.models import User, UserRole, UserStatus
from app.repositories import (
    DepartmentRepository,
    SessionRepository,
    StudentRepository,
    UserRepository,
)
from app.services.audit_logs import AuditLogService
from app.services.base import BaseService
from app.services.email import EmailService
from app.services.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.sessions import SessionService
from app.utils.time import utc_now


@dataclass(frozen=True)
class LoginResult:
    """Authenticated session result for the login endpoint."""

    user: User
    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int


def _ensure_aware(value: datetime | None) -> datetime | None:
    """Interpret naive UTC timestamps (SQLite round-trips) as timezone-aware.

    SQLite stores ``DateTime(timezone=True)`` columns without an offset, so a
    value reloaded from the database compares against ``utc_now()`` as naive.
    PostgreSQL round-trips aware timestamps unchanged.
    """
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class AuthService(BaseService):
    """Identity lifecycle operations (BACKEND_ARCHITECTURE.md §9)."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        users: UserRepository | None = None,
        students: StudentRepository | None = None,
        departments: DepartmentRepository | None = None,
        sessions: SessionRepository | None = None,
        audit: AuditLogService | None = None,
        email: EmailService | None = None,
    ) -> None:
        super().__init__(session)
        self._settings = settings or get_settings()
        self._users = users or UserRepository(session)
        self._students = students or StudentRepository(session)
        self._departments = departments or DepartmentRepository(session)
        self._sessions = sessions or SessionRepository(session)
        self._session_service = SessionService(
            session, sessions=self._sessions, users=self._users
        )
        self._audit = audit or AuditLogService(session, users=self._users)
        self._email = email or EmailService(self._settings)

    # -- registration -------------------------------------------------------

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        enrollment_no: str | None = None,
        department_id: uuid.UUID | None = None,
        program_name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Create a pending student account and send its verification email.

        Raises 409 on a duplicate email/enrollment number, 404 on an unknown
        department, and 422 when the password violates the strength policy.
        """
        email = self._validate_not_blank(email, field="email").lower()
        full_name = self._validate_not_blank(full_name, field="full_name")
        self._validate_not_blank(password, field="password")
        self._raise_for_password_policy(password)
        await self._require_available_email(email)
        if department_id is not None and not await self._department_exists(
            department_id
        ):
            raise NotFoundError(message="Department not found")
        if enrollment_no is not None and await self._enrollment_in_use(
            enrollment_no
        ):
            raise ConflictError(
                message="This enrollment number is already in use",
                details=[{"field": "enrollment_no", "reason": "already in use"}],
            )

        password_hash = await hash_password_async(password)
        user = await self._users.create(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=UserRole.STUDENT,
            status=UserStatus.PENDING,
        )
        if enrollment_no is not None:
            await self._students.create(
                user_id=user.id,
                enrollment_no=enrollment_no,
                department_id=department_id,
                program_name=program_name,
            )

        token = create_email_verification_token(
            subject=str(user.id), settings=self._settings
        )
        await self._email.send_verification_email(
            email=email, full_name=full_name, token=token
        )
        await self._audit.create_log(
            action="register",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return user

    # -- email verification -------------------------------------------------

    async def verify_email(
        self,
        *,
        token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Activate the account addressed by a signed verification token.

        Idempotent: verifying an already-verified account returns it unchanged.
        """
        claims = self._decode_typed_token(
            token, expected_type=TOKEN_TYPE_EMAIL_VERIFICATION
        )
        user = await self._require_user(claims.subject)
        if user.email_verified_at is not None:
            return user
        updated = await self._users.update(
            user, email_verified_at=utc_now(), status=UserStatus.ACTIVE
        )
        await self._audit.create_log(
            action="verify_email",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return updated

    # -- login --------------------------------------------------------------

    async def login(
        self,
        *,
        email: str,
        password: str,
        remember_me: bool = False,
        device_name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResult:
        """Authenticate credentials and issue an access + refresh token pair.

        Email verification is mandatory before the first login; locked,
        suspended, and deactivated accounts are rejected with a generic 401 so
        account existence is never revealed. Failed attempts are counted and
        the account locks at the configured threshold; any successful login
        resets the counters. ``remember_me`` extends the refresh-token lifetime.
        """
        email = self._validate_not_blank(email, field="email").lower()
        self._validate_not_blank(password, field="password")
        now = utc_now()

        user = await self._users.get_by_email(email)
        if user is None:
            raise UnauthorizedError(message="Invalid email or password")
        locked_until = _ensure_aware(user.locked_until)
        if locked_until is not None and locked_until > now:
            raise UnauthorizedError(
                message="Account is temporarily locked due to too many failed attempts"
            )

        if not await verify_password_async(password, user.password_hash):
            await self._record_failed_attempt(user, now)
            raise UnauthorizedError(message="Invalid email or password")

        if user.email_verified_at is None:
            raise ForbiddenError(message="Email verification is required before login")
        if user.status != UserStatus.ACTIVE:
            raise ForbiddenError(message="Account is disabled or suspended")

        await self._users.update(
            user,
            last_login_at=now,
            failed_login_attempts=0,
            locked_until=None,
        )

        refresh_token = generate_refresh_token()
        refresh_lifetime = timedelta(
            days=self._settings.remember_me_expire_days
            if remember_me
            else self._settings.refresh_token_expire_days
        )
        jti = generate_jti()
        access_token = create_access_token(
            subject=str(user.id), role=user.role.value, settings=self._settings, jti=jti
        )
        await self._session_service.create_session(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=now + refresh_lifetime,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
            access_jti=jti,
        )
        await self._enforce_session_limit(user.id)
        await self._audit.create_log(
            action="login",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return LoginResult(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_in=int(
                timedelta(minutes=self._settings.access_token_expire_minutes).total_seconds()
            ),
            refresh_expires_in=int(refresh_lifetime.total_seconds()),
        )

    # -- refresh / logout ----------------------------------------------------

    async def rotate_refresh(
        self,
        *,
        refresh_token: str,
        device_name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResult:
        """Rotate a valid refresh token into a new access + refresh pair (§5.4).

        The presented session must be unrevoked, unrotated, unexpired, and bound
        to an active user. Rotation revokes the old session and links the new
        one through ``replaced_by_session_id``; presenting a token whose session
        was already revoked or rotated revokes the entire rotation chain and
        forces a fresh login (replay detection, API_SPECIFICATION.md §5.4).
        """
        refresh_token = self._validate_not_blank(refresh_token, field="refresh_token")
        now = utc_now()
        session = await self._sessions.get_by_refresh_hash(
            hash_refresh_token(refresh_token)
        )
        if session is None:
            raise UnauthorizedError(message="Invalid or expired refresh token")

        expires_at = _ensure_aware(session.expires_at)
        created_at = _ensure_aware(session.created_at)
        if session.revoked_at is not None or session.replaced_by_session_id is not None:
            chain = await self._sessions.get_chain(session)
            await self._sessions.revoke_sessions(chain)
            await self.commit()
            raise UnauthorizedError(message="Refresh token was reused; sign in again")
        assert expires_at is not None and created_at is not None
        if expires_at <= now:
            raise UnauthorizedError(message="Refresh token has expired; sign in again")

        user = await self._users.get_by_id(session.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise UnauthorizedError(message="Invalid or expired refresh token")

        new_refresh_token = generate_refresh_token()
        lifetime = expires_at - created_at
        new_jti = generate_jti()
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            settings=self._settings,
            jti=new_jti,
        )
        new_session = await self._session_service.create_session(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(new_refresh_token),
            expires_at=now + lifetime,
            device_name=device_name or session.device_name,
            ip_address=ip_address,
            user_agent=user_agent,
            access_jti=new_jti,
        )
        await self._sessions.update(session, revoked_at=now)
        await self._sessions.update(
            new_session,
            replaced_by_session_id=session.id,
            last_used_at=now,
        )
        await self._audit.create_log(
            action="refresh",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return LoginResult(
            user=user,
            access_token=access_token,
            refresh_token=new_refresh_token,
            access_expires_in=int(
                timedelta(
                    minutes=self._settings.access_token_expire_minutes
                ).total_seconds()
            ),
            refresh_expires_in=int(lifetime.total_seconds()),
        )

    async def logout(
        self,
        *,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Revoke the session bound to ``refresh_token`` (§3.4, §5.5).

        Idempotent: an unknown or already-revoked token succeeds silently so a
        client can always log out without an extra error path.
        """
        refresh_token = self._validate_not_blank(refresh_token, field="refresh_token")
        session = await self._sessions.get_by_refresh_hash(
            hash_refresh_token(refresh_token)
        )
        if session is None or session.revoked_at is not None:
            return
        await self._sessions.revoke_session(session)
        await self._audit.create_log(
            action="logout",
            resource_type="user",
            resource_id=str(session.user_id),
            actor_user_id=session.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def logout_all(
        self,
        *,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> int:
        """Revoke every session of the refresh token's owner (§5.5).

        Returns the number of sessions revoked. The presented token must resolve
        to a live session so the caller is authenticated before a blanket revoke.
        """
        refresh_token = self._validate_not_blank(refresh_token, field="refresh_token")
        session = await self._sessions.get_by_refresh_hash(
            hash_refresh_token(refresh_token)
        )
        if session is None:
            raise UnauthorizedError(message="Invalid or expired refresh token")
        revoked = await self._session_service.revoke_all_sessions(
            user_id=session.user_id
        )
        await self._audit.create_log(
            action="logout_all",
            resource_type="user",
            resource_id=str(session.user_id),
            actor_user_id=session.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return revoked

    # -- password management ------------------------------------------------

    async def forgot_password(
        self,
        *,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Issue a single-use password-reset token and email its link (§16).

        Always succeeds from the caller's perspective (a generic response is
        returned whether or not the email exists) so account existence is
        never revealed. Only active accounts receive a reset email.
        """
        email = self._validate_not_blank(email, field="email").lower()
        user = await self._users.get_by_email(email)
        if user is None or user.status != UserStatus.ACTIVE:
            return

        now = utc_now()
        token = create_password_reset_token(subject=str(user.id), settings=self._settings)
        await self._users.update(
            user,
            password_reset_token_hash=hash_password_reset_token(token),
            password_reset_token_expires_at=now
            + timedelta(minutes=self._settings.password_reset_expire_minutes),
        )
        await self._email.send_password_reset_email(
            email=user.email, full_name=user.full_name, token=token
        )
        await self._audit.create_log(
            action="forgot_password",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def reset_password(
        self,
        *,
        token: str,
        new_password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Set a new password from a valid reset token and force re-login (§16).

        The token must be signed for the password-reset purpose, unexpired, and
        match the digest stored at issue time. Success updates the password
        hash, invalidates the token (single-use), and revokes every active
        session so the user must sign in again.
        """
        token = self._validate_not_blank(token, field="token")
        new_password = self._validate_not_blank(new_password, field="new_password")
        claims = self._decode_typed_token(
            token, expected_type=TOKEN_TYPE_PASSWORD_RESET
        )
        try:
            user_id = uuid.UUID(claims.subject)
        except ValueError as exc:
            raise UnauthorizedError(message="Invalid or expired reset token") from exc
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError(message="Invalid or expired reset token")

        stored_hash = user.password_reset_token_hash
        expires_at = _ensure_aware(user.password_reset_token_expires_at)
        if (
            stored_hash is None
            or expires_at is None
            or not secrets.compare_digest(
                stored_hash, hash_password_reset_token(token)
            )
            or expires_at <= utc_now()
        ):
            raise UnauthorizedError(message="Invalid or expired reset token")

        self._raise_for_password_policy(new_password)
        password_hash = await hash_password_async(new_password)
        updated = await self._users.update(
            user,
            password_hash=password_hash,
            password_reset_token_hash=None,
            password_reset_token_expires_at=None,
        )
        await self._session_service.revoke_all_sessions(user_id=user.id)
        await self._audit.create_log(
            action="reset_password",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return updated

    async def change_password(
        self,
        *,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
        current_session_jti: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Change an authenticated user's password (§17).

        Requires the current password (bad credentials raise ``401``), hashes
        and stores the new password, and revokes every other active session
        while leaving the acting session valid.
        """
        current_password = self._validate_not_blank(
            current_password, field="current_password"
        )
        new_password = self._validate_not_blank(new_password, field="new_password")
        user = await self._require_user(str(user_id))
        if not await verify_password_async(current_password, user.password_hash):
            raise UnauthorizedError(message="Current password is incorrect")
        self._raise_for_password_policy(new_password)

        password_hash = await hash_password_async(new_password)
        updated = await self._users.update(user, password_hash=password_hash)
        await self._session_service.revoke_other_sessions(
            user_id=user.id, except_jti=current_session_jti
        )
        await self._audit.create_log(
            action="change_password",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return updated

    # -- internals ----------------------------------------------------------

    def _raise_for_password_policy(self, password: str) -> None:
        errors = password_policy_errors(password)
        if errors:
            raise ValidationError(
                message="Password does not meet the policy requirements",
                details=[{"field": "password", "reason": reason} for reason in errors],
            )

    async def _require_available_email(self, email: str) -> None:
        if await self._users.get_by_email(email) is not None:
            raise ConflictError(
                message="A user with this email already exists",
                details=[{"field": "email", "reason": "already in use"}],
            )

    async def _department_exists(self, department_id: uuid.UUID) -> bool:
        return await self._departments.get_by_id(department_id) is not None

    async def _enrollment_in_use(self, enrollment_no: str) -> bool:
        return await self._students.get_by_enrollment_no(enrollment_no) is not None

    async def _record_failed_attempt(self, user: User, now: datetime) -> None:
        """Increment the failed-attempt counter and lock at the threshold.

        The increment is committed before the caller raises so the lockout
        survives the request-level rollback that follows the ``401``.
        """
        attempts = int(user.failed_login_attempts) + 1
        if attempts >= self._settings.lockout_threshold:
            await self._users.update(
                user,
                failed_login_attempts=attempts,
                locked_until=now + timedelta(minutes=self._settings.lockout_minutes),
            )
        else:
            await self._users.update(user, failed_login_attempts=attempts)
        await self.commit()

    def _decode_typed_token(
        self, token: str, *, expected_type: str
    ) -> TokenClaims:
        try:
            return decode_token(
                token=token, expected_type=expected_type, settings=self._settings
            )
        except pyjwt.PyJWTError as exc:
            raise UnauthorizedError(
                message="Invalid or expired token"
            ) from exc

    async def _enforce_session_limit(self, user_id: uuid.UUID) -> None:
        """Revoke oldest sessions when the user exceeds MAX_ACTIVE_SESSIONS."""
        active = await self._session_service._sessions.get_active_sessions(user_id)
        max_sessions = self._settings.max_active_sessions
        if len(active) > max_sessions:
            sorted_sessions = sorted(active, key=lambda s: s.created_at)
            to_revoke = sorted_sessions[: len(active) - max_sessions]
            for session in to_revoke:
                await self._session_service._sessions.revoke_session(session)

    async def _require_user(self, subject: str) -> User:
        try:
            user_id = uuid.UUID(subject)
        except ValueError as exc:
            raise UnauthorizedError(message="Invalid or expired token") from exc
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="User not found")
        return user

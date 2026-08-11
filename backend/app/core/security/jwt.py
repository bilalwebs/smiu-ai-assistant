"""Signed token utilities (API_SPECIFICATION.md §5; BACKEND_ARCHITECTURE.md §9).

Purpose:
    Build and validate the stateless signed tokens used by the identity
    lifecycle. Access tokens are short-lived HS256 JWTs validated with no
    database hit; email-verification tokens are purpose-scoped signed JWTs.
    Refresh tokens are opaque random strings that are only ever persisted as
    their SHA-256 digest (DATABASE_DESIGN.md §25).

Responsibilities:
    - Issue access and email-verification tokens with documented claims.
    - Decode/validate tokens (signature, issuer, audience, expiry, purpose).
    - Generate opaque refresh tokens and their 64-char SHA-256 digests.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config.settings import Settings

#: Claim carrying the token purpose; prevents cross-flow token use.
CLAIM_TYPE = "typ"

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_EMAIL_VERIFICATION = "email_verification"
TOKEN_TYPE_PASSWORD_RESET = "password_reset"


@dataclass(frozen=True)
class TokenClaims:
    """Claims decoded from a validated signed token."""

    subject: str
    token_type: str
    jti: str
    issued_at: datetime
    expires_at: datetime
    role: str | None = None


def generate_jti() -> str:
    """Return a fresh random token identifier."""
    return uuid.uuid4().hex


def _create_token(
    *,
    subject: str,
    token_type: str,
    expires_in: timedelta,
    settings: Settings,
    jti: str | None,
    extra: dict[str, Any] | None,
) -> str:
    """Encode a signed token with the documented claim set."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": jti or generate_jti(),
        "iat": now,
        "exp": now + expires_in,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        CLAIM_TYPE: token_type,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(
    *,
    subject: str,
    role: str,
    settings: Settings,
    jti: str | None = None,
) -> str:
    """Return a signed access token carrying ``sub`` and ``role``.

    ``jti`` may be supplied so the caller records the same identifier in the
    server-side session row.
    """
    return _create_token(
        subject=subject,
        token_type=TOKEN_TYPE_ACCESS,
        expires_in=timedelta(minutes=settings.access_token_expire_minutes),
        settings=settings,
        jti=jti,
        extra={"role": role},
    )


def create_email_verification_token(*, subject: str, settings: Settings) -> str:
    """Return a signed, purpose-scoped email-verification token."""
    return _create_token(
        subject=subject,
        token_type=TOKEN_TYPE_EMAIL_VERIFICATION,
        expires_in=timedelta(minutes=settings.email_verification_expire_minutes),
        settings=settings,
        jti=None,
        extra=None,
    )


def create_password_reset_token(*, subject: str, settings: Settings) -> str:
    """Return a signed, purpose-scoped password-reset token.

    The reset flow additionally persists the token's digest on the user so the
    token is single-use (invalidation, API_SPECIFICATION.md §16).
    """
    return _create_token(
        subject=subject,
        token_type=TOKEN_TYPE_PASSWORD_RESET,
        expires_in=timedelta(minutes=settings.password_reset_expire_minutes),
        settings=settings,
        jti=None,
        extra=None,
    )


#: Algorithms that are allowed to sign tokens.
_ALLOWED_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


def decode_token(
    *, token: str, expected_type: str, settings: Settings
) -> TokenClaims:
    """Validate a token and return its typed claims.

    Signature, issuer, audience, and expiry are all verified. A token whose
    purpose claim does not match ``expected_type`` is rejected.

    Raises:
        jwt.InvalidTokenError: when the token is invalid, expired, mistyped,
            or signed with an algorithm outside the allowlist.
    """
    if settings.jwt_algorithm not in _ALLOWED_ALGORITHMS:
        raise jwt.InvalidTokenError(
            f"Unsupported algorithm: {settings.jwt_algorithm}"
        )
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    _require_claims(payload, "sub", "jti", "iat", "exp")
    token_type = payload.get(CLAIM_TYPE)
    if token_type != expected_type:
        raise jwt.InvalidTokenError("Token purpose does not match the expected type")
    return TokenClaims(
        subject=str(payload["sub"]),
        token_type=str(token_type),
        jti=str(payload["jti"]),
        issued_at=datetime.fromtimestamp(float(payload["iat"]), tz=UTC),
        expires_at=datetime.fromtimestamp(float(payload["exp"]), tz=UTC),
        role=str(payload["role"]) if payload.get("role") else None,
    )


def _require_claims(payload: dict[str, Any], *names: str) -> None:
    """Raise when a required claim is absent from the payload."""
    missing = [name for name in names if name not in payload]
    if missing:
        raise jwt.InvalidTokenError(f"Missing required claim: {', '.join(missing)}")


def generate_refresh_token() -> str:
    """Return a fresh opaque refresh token (cryptographically random)."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(refresh_token: str) -> str:
    """Return the SHA-256 hex digest persisted in ``sessions.refresh_token_hash``."""
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def hash_password_reset_token(reset_token: str) -> str:
    """Return the SHA-256 hex digest persisted on ``users`` for a reset token."""
    return hashlib.sha256(reset_token.encode("utf-8")).hexdigest()

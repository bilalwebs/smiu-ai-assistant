"""Bearer JWT authentication dependency (API_SPECIFICATION.md §3, §5).

Purpose:
    Resolve the acting user (id + role) from a verified access token for every
    protected route (API_SPECIFICATION.md §4.4). Access tokens are validated
    statelessly — signature, issuer, audience, expiry, and purpose — with no
    database hit (API_SPECIFICATION.md §5.2).

Responsibilities:
    - Parse ``Authorization: Bearer <access_token>`` (headers only, §3.2).
    - Decode and type-check the access token; raise ``401`` when it is
      missing, malformed, expired, or used for the wrong purpose (§3.5).
    - Expose ``CurrentUser`` carrying the verified identity and role (§3.5).

Usage:
    ``current_user: CurrentUser = Depends(get_current_user)``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import get_settings
from app.core.security.jwt import TOKEN_TYPE_ACCESS, decode_token
from app.exceptions.app_error import UnauthorizedError

#: Scheme prefix required on every authenticated request (§3.2).
AUTH_SCHEME = "Bearer"

#: FastAPI HTTP bearer security scheme. Declared as a dependency of
#: :func:`get_current_user` so the generated OpenAPI schema advertises an
#: ``http``/``bearer`` security scheme and Swagger UI renders the
#: ``Authorize`` button, which then sends ``Authorization: Bearer <token>``
#: on every protected operation. ``auto_error=False`` keeps 401 handling in
#: :func:`_extract_bearer_token`, preserving the existing
#: ``UnauthorizedError`` behaviour.
bearer_scheme = HTTPBearer(scheme_name="BearerAuth", auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """Verified identity resolved for the current request (§3.5)."""

    user_id: uuid.UUID
    role: str
    session_jti: str | None = None


def _extract_bearer_token(request: Request) -> str:
    """Return the bearer token from the ``Authorization`` header, or raise 401."""
    header = request.headers.get("authorization")
    if not header:
        raise UnauthorizedError(message="Authentication is required")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != AUTH_SCHEME.lower() or not token:
        raise UnauthorizedError(message="Invalid authorization header")
    return token.strip()


def get_current_user(
    request: Request,
    _credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> CurrentUser:
    """Resolve the verified user id and role from the bearer access token.

    Signature, issuer, audience, expiry, and token purpose are verified here;
    role and identity come only from the verified token, never client input
    (API_SPECIFICATION.md §3.5).

    ``_credentials`` is injected solely so FastAPI registers ``bearer_scheme``
    in the OpenAPI security schemes; the token is still parsed from the raw
    ``Authorization`` header by :func:`_extract_bearer_token`, so tokens are
    never accepted from query parameters, the request body, cookies, or any
    other client-supplied channel.
    """
    token = _extract_bearer_token(request)
    try:
        claims = decode_token(
            token=token, expected_type=TOKEN_TYPE_ACCESS, settings=get_settings()
        )
        user_id = uuid.UUID(claims.subject)
        role = claims.role
        if not role:
            raise pyjwt.InvalidTokenError("Access token is missing the role claim")
    except (pyjwt.PyJWTError, ValueError):
        raise UnauthorizedError(message="Invalid or expired token") from None
    return CurrentUser(user_id=user_id, role=role, session_jti=claims.jti)

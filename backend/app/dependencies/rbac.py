"""Role-based authorization dependencies (API_SPECIFICATION.md §4).

Purpose:
    Gate protected routes by the verified ``role`` claim on the access token.
    Enforcement is server-side only and deny-by-default: access is granted
    explicitly per route (API_SPECIFICATION.md §4.1). Unauthenticated callers
    fail in :func:`app.dependencies.auth.get_current_user` with ``401``;
    authenticated callers lacking the required role or permission fail here
    with ``403``.

Responsibilities:
    - ``require_roles``: accept only callers whose token role is in a set.
    - ``require_permission``: accept only callers whose token role maps to a
      capability in the permission registry.
    - Expose stable permission names for admin endpoints (§4.3).

Usage:
    ``current_user: CurrentUser = Depends(require_roles(UserRole.ADMIN))``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from app.dependencies.auth import CurrentUser, get_current_user
from app.exceptions.app_error import ForbiddenError
from app.models import UserRole


def require_roles(*roles: UserRole) -> Callable[[CurrentUser], CurrentUser]:
    """Return a dependency accepting callers whose role is in ``roles``.

    The returned dependency first resolves the verified identity (``401`` when
    missing/invalid) and then raises ``403`` when the token role is not in
    ``roles`` (API_SPECIFICATION.md §4.4).
    """

    allowed = frozenset(roles)

    def _guard(
        current_user: Annotated[CurrentUser, Depends(get_current_user)]
    ) -> CurrentUser:
        try:
            role = UserRole(current_user.role)
        except ValueError:
            role = None
        if role not in allowed:
            raise ForbiddenError(message="Insufficient permissions for this action")
        return current_user

    return _guard


def require_permission(permission: str) -> Callable[[CurrentUser], CurrentUser]:
    """Return a dependency accepting callers holding ``permission``.

    ``permission`` names a capability from :data:`PERMISSION_ROLES`; a caller
    is allowed when its token role grants that capability. Unknown permissions
    deny everyone (fail closed).
    """

    allowed = PERMISSION_ROLES.get(permission, frozenset())

    def _guard(
        current_user: Annotated[CurrentUser, Depends(get_current_user)]
    ) -> CurrentUser:
        try:
            role = UserRole(current_user.role)
        except ValueError:
            role = None
        if role not in allowed:
            raise ForbiddenError(message="Insufficient permissions for this action")
        return current_user

    return _guard


#: Capability registry (API_SPECIFICATION.md §4.3). Every admin endpoint is
#: gated through one of these names; the student role is intentionally absent.
PERMISSION_ROLES: dict[str, frozenset[UserRole]] = {
    "users:list": frozenset({UserRole.ADMIN}),
    "users:read": frozenset({UserRole.ADMIN}),
    "audit_logs:read": frozenset({UserRole.ADMIN}),
    "knowledge:manage": frozenset({UserRole.ADMIN}),
}


__all__ = ["PERMISSION_ROLES", "require_permission", "require_roles"]

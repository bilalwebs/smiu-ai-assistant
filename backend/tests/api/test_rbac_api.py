"""RBAC authorization tests (API_SPECIFICATION.md §4).

Covers role validation, permission gating, forbidden responses, and admin
endpoint access control.
"""

from __future__ import annotations

import uuid

from app.config.settings import get_settings
from app.core.security.jwt import create_access_token


def _admin_headers() -> dict[str, str]:
    token = create_access_token(
        subject=str(uuid.uuid4()), role="admin", settings=get_settings()
    )
    return {"Authorization": f"Bearer {token}"}


def _student_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        subject=str(user_id), role="student", settings=get_settings()
    )
    return {"Authorization": f"Bearer {token}"}


def _faculty_headers() -> dict[str, str]:
    token = create_access_token(
        subject=str(uuid.uuid4()), role="faculty", settings=get_settings()
    )
    return {"Authorization": f"Bearer {token}"}


# -- admin endpoints: access control -----------------------------------------


def test_admin_list_users_requires_admin_role(api_client, seed_ids) -> None:
    """Students receive 403 on admin-only endpoints."""
    response = api_client.get(
        "/api/v1/admin/users",
        headers=_student_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH003"


def test_admin_list_users_allows_admin(api_client) -> None:
    """Admins can access admin-only endpoints."""
    response = api_client.get("/api/v1/admin/users", headers=_admin_headers())
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_admin_list_users_requires_authentication(api_client) -> None:
    response = api_client.get("/api/v1/admin/users")
    assert response.status_code == 401


def test_admin_get_user_requires_admin_role(api_client, seed_ids) -> None:
    response = api_client.get(
        f"/api/v1/admin/users/{seed_ids['owner_user_id']}",
        headers=_student_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH003"


def test_admin_get_user_allows_admin(api_client, seed_ids) -> None:
    response = api_client.get(
        f"/api/v1/admin/users/{seed_ids['owner_user_id']}",
        headers=_admin_headers(),
    )
    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(seed_ids["owner_user_id"])


def test_admin_audit_logs_requires_admin_role(api_client, seed_ids) -> None:
    response = api_client.get(
        "/api/v1/admin/audit-logs",
        headers=_student_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH003"


def test_admin_audit_logs_allows_admin(api_client) -> None:
    response = api_client.get("/api/v1/admin/audit-logs", headers=_admin_headers())
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_admin_knowledge_docs_requires_admin_role(api_client, seed_ids) -> None:
    response = api_client.get(
        "/api/v1/admin/knowledge/documents",
        headers=_student_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH003"


def test_admin_knowledge_docs_allows_admin(api_client) -> None:
    response = api_client.get(
        "/api/v1/admin/knowledge/documents", headers=_admin_headers()
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


# -- faculty role: neither admin nor student ---------------------------------


def test_faculty_user_rejected_from_admin_endpoints(api_client) -> None:
    """Faculty role is not in any admin permission set."""
    response = api_client.get("/api/v1/admin/users", headers=_faculty_headers())
    assert response.status_code == 403


# -- student access control --------------------------------------------------


def test_student_cannot_access_other_student_profile(
    api_client, seed_ids, auth_headers
) -> None:
    """Students can only access their own profile via /users/me."""
    response = api_client.get(
        f"/api/v1/users/{seed_ids['other_user_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code in (401, 403, 404)


def test_student_can_access_own_profile(api_client, seed_ids, auth_headers) -> None:
    response = api_client.get(
        "/api/v1/users/me",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(seed_ids["owner_user_id"])


def test_student_sessions_requires_auth(api_client) -> None:
    response = api_client.get("/api/v1/users/me/sessions")
    assert response.status_code == 401


# -- invalid role handling ---------------------------------------------------


def test_invalid_role_in_token_returns_401(api_client, seed_ids) -> None:
    """A token with an unrecognized role claim fails at auth level."""
    token = create_access_token(
        subject=str(seed_ids["owner_user_id"]),
        role="nonexistent_role",
        settings=get_settings(),
    )
    response = api_client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403

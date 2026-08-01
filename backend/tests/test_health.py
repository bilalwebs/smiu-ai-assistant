"""Health endpoint tests (API_SPECIFICATION.md §24; DEPLOYMENT.md §20).

Covers the versioned paths under ``/api/v1`` and the orchestration aliases,
plus the response envelope and request id behaviour.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "up"
    assert payload["data"]["version"] == "0.1.0"
    assert payload["meta"]["request_id"]
    assert payload["meta"]["timestamp"].endswith("Z")


def test_readiness_when_database_reachable(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "up"
    assert payload["data"]["checks"][0]["name"] == "database"
    assert payload["data"]["checks"][0]["status"] == "up"


def test_combined_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["overall"] == "up"
    assert payload["data"]["liveness"]["status"] == "up"
    assert payload["data"]["readiness"]["status"] == "up"


def test_version(client: TestClient) -> None:
    response = client.get("/api/v1/health/version")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "smiu-ai-assistant-backend"
    assert data["version"] == "0.1.0"
    assert data["api_version"] == "1.0"
    assert data["environment"] == "testing"
    assert data["python_version"]


def test_orchestration_alias_paths(client: TestClient) -> None:
    for path in ("/health", "/health/live", "/health/ready", "/health/version"):
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        assert response.json()["success"] is True


def test_incoming_correlation_id_is_reused(client: TestClient) -> None:
    request_id = "corr-abc-123-def"
    response = client.get("/api/v1/health/live", headers={"X-Correlation-Id": request_id})
    assert response.status_code == 200
    assert response.json()["meta"]["request_id"] == request_id
    assert response.headers["x-request-id"] == request_id


def test_missing_request_id_is_generated(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    request_id = response.json()["meta"]["request_id"]
    assert len(request_id) == 32
    assert response.headers["x-request-id"] == request_id


def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "strict-transport-security" not in response.headers  # testing env only


def test_unknown_route_returns_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "VAL001"
    assert payload["error"]["message"]
    assert payload["meta"]["request_id"]

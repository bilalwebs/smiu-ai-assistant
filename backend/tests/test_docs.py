"""Swagger UI / ReDoc self-hosting tests (BACKEND_ARCHITECTURE.md §17).

Docs pages and their static assets are served from this backend (vendored
under ``backend/static/docs``, no CDN) and get a docs-scoped CSP, while API
responses keep the strict ``default-src 'none'`` policy.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_docs_page_served_with_local_assets(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    html = response.text
    assert "/static/docs/swagger-ui-bundle.js" in html
    assert "/static/docs/swagger-ui.css" in html
    assert "/openapi.json" in html
    assert "cdn.jsdelivr.net" not in html


def test_redoc_page_served_with_local_assets(client: TestClient) -> None:
    response = client.get("/redoc")
    assert response.status_code == 200
    html = response.text
    assert "/static/docs/redoc.standalone.js" in html
    assert "cdn.jsdelivr.net" not in html


def test_local_docs_assets_are_served(client: TestClient) -> None:
    for path in (
        "/static/docs/swagger-ui-bundle.js",
        "/static/docs/swagger-ui.css",
        "/static/docs/redoc.standalone.js",
        "/static/docs/favicon-32x32.png",
    ):
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        assert len(response.content) > 0


def test_docs_pages_use_docs_scoped_csp(client: TestClient) -> None:
    response = client.get("/docs")
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self' 'unsafe-inline'" in csp


def test_api_responses_keep_strict_csp(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert (
        response.headers["content-security-policy"]
        == "default-src 'none'; frame-ancestors 'none'"
    )

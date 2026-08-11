"""Security hardening tests (Milestone 4; Phase 6).

Covers: rate limiting, password max length, JWT algorithm allowlist,
concurrent session limiting, pagination clamping, and security headers.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import jwt as pyjwt
import pytest

from app.config.settings import get_settings
from app.core.security.jwt import (
    _ALLOWED_ALGORITHMS,
    TOKEN_TYPE_ACCESS,
    create_access_token,
    decode_token,
)
from app.core.security.password import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    password_policy_errors,
)
from app.middleware.rate_limit import RateLimitMiddleware, RateLimitRule
from app.repositories.base import MAX_PAGE_LIMIT

# ---------------------------------------------------------------------------
# Password max length
# ---------------------------------------------------------------------------


class TestPasswordMaxLength:
    def test_constant_value(self) -> None:
        assert PASSWORD_MAX_LENGTH == 128
        assert PASSWORD_MAX_LENGTH > PASSWORD_MIN_LENGTH

    def test_compliant_long_password_passes(self) -> None:
        pwd = "A" * 50 + "a" * 50 + "1" * 10 + "!" * 8
        errors = password_policy_errors(pwd)
        assert errors == []

    def test_oversized_password_fails(self) -> None:
        pwd = "A" + "a" * 126 + "1!"
        assert len(pwd) == 129
        errors = password_policy_errors(pwd)
        assert any("at most 128" in e for e in errors)

    def test_exactly_max_length_passes(self) -> None:
        pwd = "A" + "a" * 125 + "1!"
        assert len(pwd) == 128
        errors = password_policy_errors(pwd)
        assert errors == []


# ---------------------------------------------------------------------------
# JWT algorithm allowlist
# ---------------------------------------------------------------------------


class TestJWTAlgorithmAllowlist:
    def test_allowed_algorithms(self) -> None:
        assert frozenset({"HS256", "HS384", "HS512"}) == _ALLOWED_ALGORITHMS

    def test_hs256_works(self) -> None:
        settings = get_settings()
        token = create_access_token(subject="u1", role="student", settings=settings)
        claims = decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)
        assert claims.subject == "u1"

    def test_none_algorithm_rejected(self) -> None:
        """A token encoded with alg=none must be rejected."""
        settings = get_settings()
        payload = {
            "sub": "u1",
            "jti": "jti",
            "iat": 0,
            "exp": 9999999999,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "typ": TOKEN_TYPE_ACCESS,
            "role": "student",
        }
        token = pyjwt.encode(payload, "", algorithm="none")
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)

    def test_forced_bad_algorithm_setting_rejected(self) -> None:
        settings = get_settings()
        bad_settings = settings.model_copy(update={"jwt_algorithm": "none"})
        with pytest.raises(pyjwt.InvalidTokenError, match="Unsupported algorithm"):
            decode_token(
                token="x.y.z",
                expected_type=TOKEN_TYPE_ACCESS,
                settings=bad_settings,
            )


# ---------------------------------------------------------------------------
# Rate limiter middleware
# ---------------------------------------------------------------------------


def _make_scope(
    path: str = "/api/v1/auth/login", client: tuple[str, int] | None = ("1.2.3.4", 99)
) -> dict[str, Any]:
    return {"type": "http", "path": path, "client": client, "headers": []}


class TestRateLimitMiddleware:
    async def test_allows_requests_up_to_limit(self) -> None:
        """max_requests=3 → first 3 requests pass, 4th rejected."""
        responses: list[dict[str, Any]] = []

        async def send(msg: dict[str, Any]) -> None:
            if msg.get("type") == "http.response.start":
                responses.append(msg)

        app = AsyncMock()
        rule = RateLimitRule(max_requests=3, window_seconds=60)
        middleware = RateLimitMiddleware(app, rules={"/api/v1/auth/login": rule})
        scope = _make_scope()

        for _ in range(3):
            await middleware(scope, AsyncMock(), AsyncMock())

        assert app.call_count == 3

        # 4th request rejected
        await middleware(scope, AsyncMock(), send)
        assert app.call_count == 3
        assert responses[-1]["status"] == 429

    async def test_exceeding_limit_sends_retry_after(self) -> None:
        responses: list[dict[str, Any]] = []

        async def send(msg: dict[str, Any]) -> None:
            if msg.get("type") == "http.response.start":
                responses.append(msg)

        app = AsyncMock()
        rule = RateLimitRule(max_requests=1, window_seconds=45)
        middleware = RateLimitMiddleware(app, rules={"/api/v1/auth/login": rule})
        scope = _make_scope()

        await middleware(scope, AsyncMock(), AsyncMock())
        await middleware(scope, AsyncMock(), send)

        headers = dict(responses[-1]["headers"])
        assert b"retry-after" in headers
        assert headers[b"retry-after"] == b"45"

    async def test_window_resets_after_window_elapses(self, monkeypatch) -> None:
        """Once a window elapses the quota is granted again."""
        current_time = {"value": 1000.0}
        monkeypatch.setattr(
            "app.middleware.rate_limit.time.monotonic",
            lambda: current_time["value"],
        )
        app = AsyncMock()
        rule = RateLimitRule(max_requests=1, window_seconds=60)
        middleware = RateLimitMiddleware(app, rules={"/api/v1/auth/login": rule})
        scope = _make_scope()

        await middleware(scope, AsyncMock(), AsyncMock())
        assert app.call_count == 1

        responses: list[dict[str, Any]] = []

        async def send(msg: dict[str, Any]) -> None:
            if msg.get("type") == "http.response.start":
                responses.append(msg)

        # Still inside the window -> rejected.
        await middleware(scope, AsyncMock(), send)
        assert responses[-1]["status"] == 429

        # Window elapsed -> allowed again.
        current_time["value"] = 1061.0
        await middleware(scope, AsyncMock(), AsyncMock())
        assert app.call_count == 2

    async def test_stale_entries_evicted_on_cleanup(self, monkeypatch) -> None:
        """Periodic cleanup drops expired (IP, path) windows to bound memory."""
        current_time = {"value": 1000.0}
        monkeypatch.setattr(
            "app.middleware.rate_limit.time.monotonic",
            lambda: current_time["value"],
        )
        app = AsyncMock()
        rule = RateLimitRule(max_requests=100, window_seconds=60)
        middleware = RateLimitMiddleware(
            app, rules={"/api/v1/auth/login": rule}, cleanup_interval=60
        )

        await middleware(_make_scope(client=("1.1.1.1", 1)), AsyncMock(), AsyncMock())
        await middleware(_make_scope(client=("2.2.2.2", 2)), AsyncMock(), AsyncMock())
        assert len(middleware._windows) == 2

        # Advance past both the cleanup interval and the stale-entry threshold.
        current_time["value"] = 1000.0 + 3700
        await middleware(_make_scope(client=("3.3.3.3", 3)), AsyncMock(), AsyncMock())

        assert list(middleware._windows) == ["3.3.3.3:/api/v1/auth/login"]

    async def test_rejected_response_body_has_sys002_code(self) -> None:
        """A 429 response uses the documented SYS002 error envelope."""
        bodies: list[dict[str, Any]] = []

        async def send(msg: dict[str, Any]) -> None:
            if msg.get("type") == "http.response.body":
                bodies.append(msg)

        app = AsyncMock()
        rule = RateLimitRule(max_requests=0, window_seconds=60)
        middleware = RateLimitMiddleware(app, rules={"/api/v1/auth/login": rule})
        await middleware(_make_scope(), AsyncMock(), send)

        assert app.call_count == 0
        payload = json.loads(bodies[0]["body"])
        assert payload["success"] is False
        assert payload["error"]["code"] == "SYS002"

    async def test_non_matching_path_passes_through(self) -> None:
        app = AsyncMock()
        rule = RateLimitRule(max_requests=1, window_seconds=60)
        middleware = RateLimitMiddleware(app, rules={"/api/v1/auth/login": rule})
        scope = _make_scope(path="/api/v1/students")

        for _ in range(5):
            await middleware(scope, AsyncMock(), AsyncMock())
        assert app.call_count == 5

    async def test_different_ips_are_independent(self) -> None:
        """Each IP gets its own window."""
        app = AsyncMock()
        rule = RateLimitRule(max_requests=2, window_seconds=60)
        middleware = RateLimitMiddleware(app, rules={"/api/v1/auth/login": rule})

        scope1 = _make_scope(client=("1.1.1.1", 1))
        scope2 = _make_scope(client=("2.2.2.2", 2))

        # IP1 gets 2 requests
        await middleware(scope1, AsyncMock(), AsyncMock())
        await middleware(scope1, AsyncMock(), AsyncMock())
        # IP2 gets 2 requests (independent window)
        await middleware(scope2, AsyncMock(), AsyncMock())
        await middleware(scope2, AsyncMock(), AsyncMock())

        assert app.call_count == 4

    async def test_non_http_scope_passes_through(self) -> None:
        app = AsyncMock()
        middleware = RateLimitMiddleware(app, rules={})
        scope = {"type": "websocket"}
        await middleware(scope, AsyncMock(), AsyncMock())
        app.assert_called_once()

    async def test_x_forwarded_for_ip_extracted(self) -> None:
        """When client is None, X-Forwarded-For is used for IP identification."""
        responses: list[dict[str, Any]] = []

        async def send(msg: dict[str, Any]) -> None:
            if msg.get("type") == "http.response.start":
                responses.append(msg)

        app = AsyncMock()
        rule = RateLimitRule(max_requests=1, window_seconds=60)
        middleware = RateLimitMiddleware(app, rules={"/api/v1/auth/login": rule})

        scope = {
            "type": "http",
            "path": "/api/v1/auth/login",
            "client": None,
            "headers": [(b"x-forwarded-for", b"10.0.0.1, 10.0.0.2")],
        }

        # First request passes
        await middleware(scope, AsyncMock(), AsyncMock())
        assert app.call_count == 1

        # Second request from same forwarded IP is rejected
        await middleware(scope, AsyncMock(), send)
        assert responses[-1]["status"] == 429

    async def test_no_client_and_no_forwarded_uses_unknown(self) -> None:
        """Requests with no client and no X-Forwarded-For share an 'unknown' bucket."""
        app = AsyncMock()
        rule = RateLimitRule(max_requests=1, window_seconds=60)
        middleware = RateLimitMiddleware(app, rules={"/api/v1/auth/login": rule})

        scope = {
            "type": "http",
            "path": "/api/v1/auth/login",
            "client": None,
            "headers": [],
        }

        await middleware(scope, AsyncMock(), AsyncMock())
        assert app.call_count == 1

        responses: list[dict[str, Any]] = []

        async def send(msg: dict[str, Any]) -> None:
            if msg.get("type") == "http.response.start":
                responses.append(msg)

        await middleware(scope, AsyncMock(), send)
        assert responses[-1]["status"] == 429


# ---------------------------------------------------------------------------
# Pagination clamping
# ---------------------------------------------------------------------------


class TestPaginationClamping:
    def test_max_page_limit_constant(self) -> None:
        assert MAX_PAGE_LIMIT == 100


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    def test_permissions_policy_header_present(self) -> None:
        from app.middleware.security import _DEFAULT_HEADERS
        header_names = [h[0] for h in _DEFAULT_HEADERS]
        assert b"permissions-policy" in header_names

    def test_permissions_policy_value(self) -> None:
        from app.middleware.security import _DEFAULT_HEADERS
        perm_header = next(h for h in _DEFAULT_HEADERS if h[0] == b"permissions-policy")
        value = perm_header[1].decode()
        assert "camera=()" in value
        assert "microphone=()" in value
        assert "usb=()" in value

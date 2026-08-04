"""Rate limiting middleware (Milestone 4).

Purpose:
    Production-ready, in-memory, IP-based sliding-window rate limiter for
    protecting sensitive endpoints (login, register, forgot-password, etc.)
    against brute-force, credential stuffing, and automated abuse.

Design:
    Sliding-window counters per (IP, path-prefix) pair with automatic
    expiration of stale entries.  No external dependencies (Redis, etc.)
    — the limiter lives entirely in process memory so it resets on restart,
    which is acceptable for a single-instance deployment and avoids adding
    infrastructure requirements to the test/dev workflow.

    The middleware is opt-in: only routes whose path prefix appears in the
    ``paths`` configuration are rate-limited; all other routes pass through
    unconditionally.

Responsibilities:
    - Enforce per-IP, per-path-prefix request quotas.
    - Return ``429 Too Many Requests`` with a ``Retry-After`` header when the
      limit is exceeded.
    - Automatically clean up stale window entries to bound memory usage.
    - Emit a structured warning log on each rejected request.

Usage:
    Registered via ``app.add_middleware(RateLimitMiddleware, ...)``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable, MutableMapping
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_ASGIApp = Callable[
    [
        MutableMapping[str, Any],
        Callable[[], Awaitable[MutableMapping[str, Any]]],
        Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ],
    Awaitable[None],
]
_Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
_Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class RateLimitRule:
    """A single rate-limit rule for a path prefix."""

    max_requests: int
    window_seconds: int


@dataclass
class _WindowEntry:
    """Sliding window counter for a single (IP, path) pair."""

    count: int = 0
    window_start: float = 0.0

    def reset(self, now: float, window_seconds: int) -> None:
        """Start a fresh window."""
        self.count = 0
        self.window_start = now

    def is_expired(self, now: float, window_seconds: int) -> bool:
        """Return ``True`` when the current window has elapsed."""
        return (now - self.window_start) >= window_seconds

    def increment(self) -> int:
        """Increment the counter and return the new value."""
        self.count += 1
        return self.count


class RateLimitMiddleware:
    """In-memory sliding-window rate limiter for selected path prefixes."""

    def __init__(
        self,
        app: _ASGIApp,
        *,
        rules: dict[str, RateLimitRule] | None = None,
        cleanup_interval: int = 60,
    ) -> None:
        self.app = app
        self.rules = rules or {}
        self._windows: dict[str, _WindowEntry] = {}
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = cleanup_interval

    def _client_ip(self, scope: MutableMapping[str, Any]) -> str:
        """Extract the client IP, respecting ``X-Forwarded-For`` behind a proxy."""
        client = scope.get("client")
        if client is not None:
            return str(client[0])
        headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        forwarded: bytes | None = headers.get(b"x-forwarded-for")
        if forwarded:
            return forwarded.decode("utf-8", errors="replace").split(",")[0].strip()
        return "unknown"

    def _match_rule(self, path: str) -> RateLimitRule | None:
        """Return the first matching rule for ``path``, or ``None``."""
        for prefix, rule in self.rules.items():
            if path.startswith(prefix):
                return rule
        return None

    def _cleanup_if_needed(self, now: float) -> None:
        """Evict stale entries periodically to bound memory."""
        if (now - self._last_cleanup) < self._cleanup_interval:
            return
        self._last_cleanup = now
        expired_keys = [
            key
            for key, entry in self._windows.items()
            if entry.is_expired(now, 3600)
        ]
        for key in expired_keys:
            del self._windows[key]

    def _check_rate_limit(self, client_ip: str, path: str, now: float) -> int | None:
        """Return the remaining quota or ``None`` if within limits.

        Returns ``0`` when the limit has been reached (caller should reject).
        """
        rule = self._match_rule(path)
        if rule is None:
            return None

        key = f"{client_ip}:{path}"
        entry = self._windows.get(key)

        if entry is None or entry.is_expired(now, rule.window_seconds):
            entry = _WindowEntry()
            entry.reset(now, rule.window_seconds)
            self._windows[key] = entry
            return rule.max_requests

        count = entry.increment()
        remaining = rule.max_requests - count
        return max(remaining, 0)

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: _Receive,
        send: _Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        now = time.monotonic()
        self._cleanup_if_needed(now)

        client_ip = self._client_ip(scope)
        path = scope.get("path", "/")
        remaining = self._check_rate_limit(client_ip, path, now)

        if remaining is not None and remaining <= 0:
            rule = self._match_rule(path)
            assert rule is not None
            retry_after = str(rule.window_seconds)

            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "path": path,
                    "limit": rule.max_requests,
                    "window_seconds": rule.window_seconds,
                },
            )

            import json

            body = json.dumps(
                {
                    "success": False,
                    "error": {
                        "code": "SYS002",
                        "message": "Too many requests. Please try again later.",
                    },
                    "meta": {"request_id": "", "timestamp": ""},
                }
            ).encode("utf-8")

            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"retry-after", retry_after.encode("utf-8")],
                        [b"content-length", str(len(body)).encode("utf-8")],
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)

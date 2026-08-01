"""Security headers middleware.

Purpose:
    Emit baseline HTTP security headers on every response
    (BACKEND_ARCHITECTURE.md §8; PROJECT_RULES.md Security Best Practices).

Responsibilities:
    - Add HSTS, X-Content-Type-Options, X-Frame-Options, and a sane CSP.
    - Enable HSTS only in production.

Usage:
    Registered via ``app.add_middleware(SecurityHeadersMiddleware, ...)``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

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

_DEFAULT_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
)

_HSTS_HEADER = (b"strict-transport-security", b"max-age=31536000; includeSubDomains")


class SecurityHeadersMiddleware:
    """Append baseline security headers to every HTTP response."""

    def __init__(self, app: _ASGIApp, *, enable_hsts: bool = False) -> None:
        self.app = app
        self.enable_hsts = enable_hsts

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: _Receive,
        send: _Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(
            message: MutableMapping[str, Any],
        ) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(_DEFAULT_HEADERS)
                if self.enable_hsts:
                    message.setdefault("headers", []).append(_HSTS_HEADER)
            await send(message)

        await self.app(scope, receive, send_wrapper)

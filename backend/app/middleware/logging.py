"""Request logging + timing middleware.

Purpose:
    Log every HTTP request with method, path, status, duration, client host, and
    request id (BACKEND_ARCHITECTURE.md §16-17; PROJECT_RULES.md Logging &
    Monitoring).

Responsibilities:
    - Measure per-request latency.
    - Emit one structured log line per completed request.
    - Let exceptions propagate so the global handler still formats them.

Usage:
    Registered via ``app.add_middleware(RequestLoggingMiddleware)``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable, MutableMapping
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


class RequestLoggingMiddleware:
    """Structured access logging with duration measurement."""

    def __init__(self, app: _ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: _Receive,
        send: _Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code: int | None = None
        method = scope["method"]
        path = scope["path"]
        client = scope.get("client")

        async def send_wrapper(
            message: MutableMapping[str, Any],
        ) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "request completed",
                extra={
                    "request_id": scope.get("state", {}).get("request_id"),
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_host": client[0] if client else None,
                },
            )

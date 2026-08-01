"""Request id / correlation id middleware.

Purpose:
    Ensure every HTTP request carries a single request id used for correlation,
    logging, and error responses (API_SPECIFICATION.md §6.1, §37).

Responsibilities:
    - Reuse a valid incoming ``X-Correlation-Id`` / ``X-Request-Id`` header.
    - Generate a fresh id otherwise (validated, length-capped).
    - Expose the id via ``request.state.request_id``.
    - Echo it back on the response ``X-Request-Id`` header.

Usage:
    Registered via ``app.add_middleware(RequestIDMiddleware, ...)`` with the
    configured header names.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from starlette.datastructures import Headers

from app.utils.request_id import generate_request_id, is_valid_request_id

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


class RequestIDMiddleware:
    """Attach a request id to every HTTP request and response."""

    def __init__(
        self,
        app: _ASGIApp,
        request_id_header: str = "X-Request-Id",
        correlation_id_header: str = "X-Correlation-Id",
    ) -> None:
        self.app = app
        self.request_id_header = request_id_header
        self.correlation_id_header = correlation_id_header

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: _Receive,
        send: _Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        incoming = headers.get(self.correlation_id_header) or headers.get(
            self.request_id_header
        )
        if incoming is not None and is_valid_request_id(incoming):
            request_id = incoming[:64]
        else:
            request_id = generate_request_id()[:64]

        scope.setdefault("state", {})["request_id"] = request_id
        response_header = self.request_id_header.encode().replace(b"_", b"-")

        async def send_wrapper(
            message: MutableMapping[str, Any],
        ) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).append(
                    (response_header, request_id.encode())
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)

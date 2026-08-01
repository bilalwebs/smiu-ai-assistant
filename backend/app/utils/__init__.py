"""Pure, reusable helper modules for the backend service.

Purpose:
    Host small, generic, layer-appropriate helpers shared across modules.

Responsibilities:
    - Time utilities (UTC now).
    - Request/correlation id generation and access.
    - Response envelope builders.

Usage:
    Import specific helpers directly, e.g.
    ``from app.utils.response import success_response``.
"""

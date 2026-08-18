"""API version v1 package.

Purpose:
    Versioned v1 API — routes nested under ``/api/v1``
    (API_SPECIFICATION.md §3; BACKEND_ARCHITECTURE.md §17).

Responsibilities:
    - Aggregate all v1 endpoint routers into a single ``api_router``.
    - Declare the shared v1 dependencies/tags.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    ai,
    auth,
    conversations,
    documents,
    health,
    knowledge,
    messages,
    notifications,
    requests,
    students,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(students.router)
api_router.include_router(requests.router)
api_router.include_router(notifications.router)
api_router.include_router(conversations.router)
api_router.include_router(documents.router)
api_router.include_router(messages.router)
api_router.include_router(knowledge.router)
api_router.include_router(ai.router)
api_router.include_router(admin.router)

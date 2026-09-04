"""FastAPI application entrypoint for the SMU AI Assistant backend service.

Purpose:
    Expose the WSGI/ASGI application object for ``uvicorn``
    (BACKEND_ARCHITECTURE.md §15.1; IMPLEMENTATION_PLAN.md Phase 1).

Usage:
    Run locally with ``uvicorn app.main:app --reload`` from ``backend/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The ``ai`` package lives at the repository root (one level above ``backend/``).
# Adding the project root to sys.path makes ``from ai.graphs.workflow import ...``
# resolve correctly when the backend is started from the ``backend/`` directory.
_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.core.app_factory import create_app

app = create_app()

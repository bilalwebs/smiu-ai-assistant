"""``/ai/chat`` API tests (API_SPECIFICATION.md §21.1-21.4).

The real app is built fresh so the ``get_ai_chat_service`` dependency can be
overridden with an offline fake-workflow service; the shared in-memory DB is
seeded exactly as ``api_client`` does (TESTING_STRATEGY.md §16).
"""

from __future__ import annotations

import uuid
from typing import Annotated

import pytest
from ai.core.config import Settings
from ai.core.state import AgentKey as AIAgentKey
from ai.graphs.workflow import build_workflow
from ai.memory.manager import ConversationMemoryManager
from ai.tests.test_admission import FakeGateway, FakeRetriever, _chunk, _llm_json
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.app_factory import create_app
from app.dependencies.database import get_db_session
from app.dependencies.services import get_ai_chat_service
from app.services import AIChatService

ChatSession = Annotated[AsyncSession, Depends(get_db_session)]

_ADMISSION_QUERY = "What are the admission requirements for BSCS?"


def _build_workflow(retriever_chunks: list | None = None) -> object:
    """Compile the graph offline: rule-based Coordinator + fake specialists."""
    from ai.agents.admission import create_admission_agent
    from ai.agents.coordinator import create_coordinator
    from ai.agents.examination import create_examination_agent
    from ai.agents.faq import create_faq_agent

    settings = Settings(_env_file=None)
    chunks = retriever_chunks if retriever_chunks is not None else [_chunk("abc123")]
    admission = create_admission_agent(
        settings=settings,
        retriever=FakeRetriever(chunks),
        gateway=FakeGateway(
            content=_llm_json(
                answer="You are eligible with 60% in intermediate.",
                cited_chunk_ids=[chunk.chunk_id for chunk in chunks],
            )
        ),
    )
    examination = create_examination_agent(
        settings=settings,
        retriever=FakeRetriever(),
        gateway=FakeGateway(
            content=_llm_json(answer="Date sheets are published per semester.")
        ),
    )
    faq = create_faq_agent(
        settings=settings,
        retriever=FakeRetriever(),
        gateway=FakeGateway(content=_llm_json(answer="The library opens at 8am.")),
    )
    memory = ConversationMemoryManager(chat_history_limit=settings.chat_history_limit)
    return build_workflow(
        coordinator=create_coordinator(),
        memory=memory,
        specialists={
            AIAgentKey.ADMISSION: admission,
            AIAgentKey.EXAMINATION: examination,
            AIAgentKey.FAQ: faq,
        },
    )


def _build_app(*, retriever_chunks: list | None = None) -> TestClient:
    """Build a fresh app with the fake-workflow chat service injected."""

    def override_chat_service(db: ChatSession) -> AIChatService:
        return AIChatService(db, workflow=_build_workflow(retriever_chunks))

    app = create_app()
    app.dependency_overrides[get_ai_chat_service] = override_chat_service
    return TestClient(app)


@pytest.fixture()
def chat_client() -> TestClient:
    """Seeded TestClient with the fake-workflow chat service."""
    from app.config.settings import clear_settings_cache
    from app.database.session import reset_engine
    from tests.api.conftest import _seed_database

    clear_settings_cache()
    reset_engine()
    _seed_database()
    client = _build_app()
    yield client
    client.close()
    clear_settings_cache()
    reset_engine()


@pytest.fixture()
def chat_client_with_citation() -> TestClient:
    """Same as ``chat_client`` but the admission retriever returns ``vec-1``."""
    from app.config.settings import clear_settings_cache
    from app.database.session import reset_engine
    from tests.api.conftest import _seed_database

    clear_settings_cache()
    reset_engine()
    _seed_database()
    client = _build_app(retriever_chunks=[_chunk("vec-1", score=0.91)])
    yield client
    client.close()
    clear_settings_cache()
    reset_engine()


def test_chat_creates_conversation_and_returns_answer(
    chat_client, seed_ids, auth_headers
) -> None:
    response = chat_client.post(
        "/api/v1/ai/chat",
        json={"message": _ADMISSION_QUERY},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer"] == "You are eligible with 60% in intermediate."
    assert data["status"] == "completed"
    assert data["active_agent"] == "admission"
    assert data["handoff"]["previous_agent"] == "coordinator"
    assert data["handoff"]["routed_to"] == "admission"
    assert len(data["citations"]) == 1
    assert data["citations"][0]["source_title"] == "Admission Policy"
    assert data["conversation_id"] != str(seed_ids["conversation_id"])
    assert data["user_message_id"] != data["assistant_message_id"]


def test_chat_continues_owned_conversation(chat_client, seed_ids, auth_headers) -> None:
    response = chat_client.post(
        "/api/v1/ai/chat",
        json={
            "message": "When is the exam?",
            "conversation_id": str(seed_ids["conversation_id"]),
        },
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["conversation_id"] == str(seed_ids["conversation_id"])
    assert data["active_agent"] == "examination"


def test_chat_citation_resolves_seeded_chunk(
    chat_client_with_citation, seed_ids, auth_headers
) -> None:
    response = chat_client_with_citation.post(
        "/api/v1/ai/chat",
        json={"message": _ADMISSION_QUERY},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["citations"]) == 1
    citation = data["citations"][0]
    assert citation["knowledge_document_id"] == str(seed_ids["document_id"])
    assert citation["knowledge_chunk_id"] == str(seed_ids["chunk_id"])
    assert citation["source_title"] == "Admission Policy"


def test_chat_foreign_conversation_is_404(chat_client, seed_ids, auth_headers) -> None:
    response = chat_client.post(
        "/api/v1/ai/chat",
        json={
            "message": "Hello",
            "conversation_id": str(seed_ids["conversation_id"]),
        },
        headers=auth_headers(seed_ids["other_user_id"]),
    )
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_chat_unknown_conversation_is_404(chat_client, seed_ids, auth_headers) -> None:
    response = chat_client.post(
        "/api/v1/ai/chat",
        json={"message": "Hello", "conversation_id": str(uuid.uuid4())},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_chat_requires_authentication(chat_client) -> None:
    response = chat_client.post("/api/v1/ai/chat", json={"message": "Hello"})
    assert response.status_code == 401


def test_chat_blank_message_is_422(chat_client, seed_ids, auth_headers) -> None:
    response = chat_client.post(
        "/api/v1/ai/chat",
        json={"message": "   "},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422


def test_chat_message_too_long_is_422(chat_client, seed_ids, auth_headers) -> None:
    response = chat_client.post(
        "/api/v1/ai/chat",
        json={"message": "a" * 4001},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422


__all__ = []

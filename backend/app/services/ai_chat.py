"""AI chat facade (BACKEND_ARCHITECTURE.md §20; API_SPECIFICATION.md §21).

Purpose:
    Step A of the AI integration boundary: bridge the agentic workflow into the
    backend so ``POST /api/v1/ai/chat`` runs the Coordinator → specialist → RAG
    pipeline and persists the exchange into the existing chat tables
    (``ai_conversations``, ``chat_history``, ``ai_sources``). The AI layer stays
    a first-class boundary: the workflow is injected (tests) or built lazily
    from ``ai`` settings (production), and persistence always flows through the
    backend services — never direct AI writes (BACKEND_ARCHITECTURE.md §20).
    Step B adds the conversation memory integration (§21, §22.5): session memory
    is rebuilt from the persisted ``chat_history`` rows and the workflow's
    ``persist_writer`` is wired to a backend adapter
    (:class:`~app.services.ai_memory.ConversationMemoryWriter`) that records the
    window and flushes the opt-in long-term summary — without duplicating any
    message or source.

Responsibilities:
    - resolve or create the conversation, append the user turn,
    - rebuild the short-term memory window from persisted history (§21.4,
      §22.5) and build the ``WorkflowState`` (query, identity, memory window,
      active agent) and run the compiled graph,
    - persist the assistant answer with the routed agent and handoff metadata,
    - persist citations as ``ai_sources`` rows, resolving vector chunk ids back
      to the knowledge base (§21.4),
    - flush the long-term summary through the memory writer best-effort
      (§21.3, §23.1),
    - degrade construction failures (missing index, unconfigured gateway) to a
      503 ``AI005`` instead of leaking internals.

Safety:
    - the user message is recorded append-only regardless of the AI outcome,
    - a memory persistence failure never fails the run: the graph swallows
      ``persist_writer`` errors (§23.1) and the summary flush is best-effort,
    - a missing/corrupt index or unconfigured LLM gateway raises
      ``AIUnavailableError`` (HTTP 503, ``AI005``) before any conversation is
      created,
    - raw provider errors and secrets never reach the API (API_SPECIFICATION.md
      §26 ``AI`` domain).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentKey,
    ConversationStatus,
    MessageRole,
    MessageStatus,
    SourceType,
)
from app.repositories import (
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)
from app.schemas.ai import ChatCitationRead, ChatResponse, HandoffRead
from app.services.ai_conversations import ConversationService
from app.services.ai_memory import ConversationMemoryWriter
from app.services.ai_sources import AISourceService
from app.services.base import BaseService
from app.services.chat_history import ChatHistoryService
from app.services.exceptions import AIUnavailableError, InvalidStateError

if TYPE_CHECKING:
    from ai.core.state import AgentKey as AIAgentKey
    from ai.core.state import WorkflowState

logger = logging.getLogger(__name__)

#: Roles carried into the memory window; SYSTEM/TOOL rows never reach context.
_HISTORY_ROLES = frozenset({MessageRole.USER, MessageRole.ASSISTANT})


class AIChatService(BaseService):
    """Bridge between the agentic workflow and the backend chat tables."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        conversations: ConversationService | None = None,
        chat_history: ChatHistoryService | None = None,
        sources: AISourceService | None = None,
        chunks: KnowledgeChunkRepository | None = None,
        documents: KnowledgeDocumentRepository | None = None,
        workflow: Any | None = None,
        settings: Any | None = None,
        memory: Any | None = None,
        memory_writer: ConversationMemoryWriter | None = None,
    ) -> None:
        super().__init__(session)
        self._conversations = conversations or ConversationService(session)
        self._chat_history = chat_history or ChatHistoryService(session)
        self._sources = sources or AISourceService(session)
        self._chunks = chunks or KnowledgeChunkRepository(session)
        self._documents = documents or KnowledgeDocumentRepository(session)
        #: Compiled workflow graph. Injected in tests; built lazily in production.
        self._workflow = workflow
        self._settings = settings
        #: Conversation memory. Injected in tests; derived lazily from the
        #: ``ai`` settings in production (§21). The writer is the backend side
        #: of the workflow's ``persist_writer`` boundary (§21.2, §23.1); it
        #: defaults to an adapter over the facade's own conversation service.
        self._memory = memory
        self._memory_writer = memory_writer

    async def chat(
        self,
        *,
        user_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None = None,
        department_id: uuid.UUID | None = None,
        user_role: str = "student",
        document_ids: list[uuid.UUID] | None = None,
    ) -> ChatResponse:
        """Run one agentic turn and persist the exchange (§21).

        Raises:
            ``NotFoundError``    conversation does not exist,
            ``InvalidStateError`` conversation is not active,
            ``AIUnavailableError`` (503 ``AI005``) the workflow cannot be built
            or did not produce a response.
        """
        content = self._validate_not_blank(message, field="message")

        user_doc_texts = await self._load_user_document_texts(
            user_id=user_id,
            document_ids=document_ids or [],
        )

        workflow = self._build_workflow()

        if conversation_id is None:
            conversation = await self._conversations.create_conversation(
                user_id=user_id,
                department_id=department_id,
            )
            session_history: list[Any] = []
            session_summary: str | None = None
        else:
            conversation = await self._conversations.get_conversation(
                conversation_id=conversation_id
            )
            if conversation.status != ConversationStatus.ACTIVE:
                raise InvalidStateError(
                    message="Conversation is not active",
                    details=[{"field": "conversation_id", "reason": "not active"}],
                )
            session = await self._rebuild_session_memory(conversation)
            session_history = session.history
            session_summary = session.summary

        user_message = await self._chat_history.add_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
            status=MessageStatus.COMPLETED,
        )

        await self._link_documents_to_message(
            user_id=user_id,
            document_ids=document_ids or [],
            message_id=user_message.id,
        )

        state = await self._invoke_workflow(
            workflow,
            user_id=user_id,
            user_role=user_role,
            content=content,
            conversation=conversation,
            history=session_history,
            user_doc_texts=user_doc_texts,
        )

        active_agent = state.current_agent
        agent_output = state.agent_output
        if agent_output is None:
            raise AIUnavailableError(
                message="The AI assistant did not produce a response; please try again."
            )

        assistant_message = await self._chat_history.add_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            agent_key=(
                AgentKey(active_agent.value)
                if active_agent is not None
                else None
            ),
            content=agent_output.answer,
            status=MessageStatus.COMPLETED,
            parent_message_id=user_message.id,
        )

        if active_agent is not None:
            await self._conversations.update_conversation(
                conversation_id=conversation.id,
                current_agent=AgentKey(active_agent.value),
            )

        citations = await self._persist_citations(
            message_id=assistant_message.id,
            citations=agent_output.citations,
        )

        if session_summary is not None:
            writer = self._get_memory_writer()
            try:
                await writer.flush(
                    conversation_id=conversation.id,
                    summary=session_summary,
                )
            except Exception:
                logger.exception("Failed to flush conversation memory summary")

        return ChatResponse(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer=agent_output.answer,
            status=agent_output.status.value,
            active_agent=(
                AgentKey(active_agent.value) if active_agent is not None else None
            ),
            handoff=self._to_handoff(state.handoff),
            citations=citations,
        )

    # -- user document context -----------------------------------------------

    async def _load_user_document_texts(
        self,
        *,
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID],
    ) -> list[str]:
        """Load extracted text from user-uploaded documents.

        Verifies that each document belongs to the acting user and has
        successfully extracted text. Returns a list of text strings in the
        order the document IDs were provided. Non-existent, unauthorized,
        or failed documents are silently skipped.
        """
        if not document_ids:
            return []

        from app.models import Document
        from app.utils.file_storage import read_extracted_text

        texts: list[str] = []
        for doc_id in document_ids:
            doc = await self._session.get(Document, doc_id)
            if doc is None:
                continue
            if doc.user_id != user_id:
                continue
            if doc.extracted_text_path is None:
                continue
            text = read_extracted_text(doc.extracted_text_path)
            if text:
                texts.append(text)
        return texts

    async def _link_documents_to_message(
        self,
        *,
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID],
        message_id: uuid.UUID,
    ) -> None:
        """Link owned documents to the user message after creation.

        Sets ``message_id`` on each document so the existing
        ``Document.message_id`` FK (→ ``chat_history.id``) creates the
        indirect path Document → ChatMessage → AIConversation.
        Non-existent or unauthorized documents are silently skipped.
        """
        if not document_ids:
            return

        from app.models import Document

        for doc_id in document_ids:
            doc = await self._session.get(Document, doc_id)
            if doc is None:
                continue
            if doc.user_id != user_id:
                continue
            doc.message_id = message_id
        await self._session.flush()

    # -- workflow construction ------------------------------------------------

    def _build_workflow(self) -> Any:
        """Return the compiled graph, building it lazily from ``ai`` settings.

        Construction requires a persisted vector index and a configured LLM
        gateway; either missing surfaces as ``AIUnavailableError`` (503
        ``AI005``) rather than a crash. Imports stay lazy so the facade is
        importable even when the AI runtime is unavailable.
        """
        if self._workflow is not None:
            return self._workflow

        try:
            from ai.agents.admission import create_admission_agent
            from ai.agents.coordinator import create_llm_coordinator
            from ai.agents.examination import create_examination_agent
            from ai.agents.faq import create_faq_agent
            from ai.core.config import get_settings
            from ai.core.state import AgentKey as AIAgentKey
            from ai.gateway.base import LLMConfigurationError
            from ai.gateway.factory import build_llm_gateway
            from ai.graphs.workflow import build_workflow
            from ai.rag.embeddings import EmbeddingProviderError
            from ai.rag.faiss_index import FaissIndexError
            from ai.rag.faiss_retriever import IndexUnavailableError, create_faiss_retriever

            settings = self._settings if self._settings is not None else get_settings()
            retriever = create_faiss_retriever(settings)
            gateway = build_llm_gateway(settings)
        except ImportError as exc:
            raise AIUnavailableError(
                message="The AI assistant is not ready yet; please try again later."
            ) from exc
        except (
            EmbeddingProviderError,
            IndexUnavailableError,
            FaissIndexError,
            LLMConfigurationError,
        ) as exc:
            raise AIUnavailableError(
                message="The AI assistant is not ready yet; please try again later."
            ) from exc

        coordinator = create_llm_coordinator(settings=settings, gateway=gateway)
        specialists: dict[AIAgentKey, Any] = {
            AIAgentKey.ADMISSION: create_admission_agent(
                settings=settings,
                retriever=retriever,
                gateway=gateway,
            ),
            AIAgentKey.EXAMINATION: create_examination_agent(
                settings=settings,
                retriever=retriever,
                gateway=gateway,
            ),
            AIAgentKey.FAQ: create_faq_agent(
                settings=settings,
                retriever=retriever,
                gateway=gateway,
            ),
        }
        memory = self._get_memory()
        self._workflow = build_workflow(
            coordinator=coordinator,
            memory=memory,
            specialists=specialists,
            persist_writer=self._get_memory_writer(),
        )
        return self._workflow

    # -- workflow invocation --------------------------------------------------

    async def _invoke_workflow(
        self,
        workflow: Any,
        *,
        user_id: uuid.UUID,
        user_role: str,
        content: str,
        conversation: Any,
        history: list[Any],
        user_doc_texts: list[str] | None = None,
    ) -> WorkflowState:
        """Build the typed state and run the compiled graph off the event loop."""
        from ai.core.state import (
            UserContext,
            UserRole,
            WorkflowState,
        )

        role = UserRole(user_role) if user_role in UserRole else UserRole.STUDENT
        current_agent: AIAgentKey | None = None
        if conversation.current_agent is not None:
            current_agent = self._to_ai_agent(conversation.current_agent)

        state = WorkflowState(
            user_query=content,
            conversation_id=conversation.id,
            user_context=UserContext(
                user_id=user_id,
                user_role=role,
            ),
            current_agent=current_agent,
            message_history=history,
            user_document_texts=user_doc_texts or [],
        )
        result = await asyncio.to_thread(workflow.invoke, state.model_dump())
        return WorkflowState.model_validate(result)

    # -- memory -------------------------------------------------------------

    def _get_memory(self) -> Any:
        """Return the conversation memory (injected or lazy from settings)."""
        if self._memory is not None:
            return self._memory
        if self._settings is None:
            from ai.core.config import get_settings

            self._settings = get_settings()
        from ai.memory.manager import ConversationMemoryManager

        return ConversationMemoryManager(
            chat_history_limit=self._settings.chat_history_limit
        )

    def _get_memory_writer(self) -> ConversationMemoryWriter:
        """Return the memory writer (injected or built on the chat services).

        The default writer reuses the facade's own ``ConversationService`` so
        the workflow's ``persist_writer`` boundary is wired in production with
        no DI changes and no new persistence path (§20, §21.2, §23.1).
        """
        if self._memory_writer is None:
            self._memory_writer = ConversationMemoryWriter(self._conversations)
        return self._memory_writer

    async def _rebuild_session_memory(self, conversation: Any) -> Any:
        """Reconstruct session memory from persisted data (§21.4, §22.5).

        The short-term window is derived from the persisted ``chat_history``
        rows (USER/ASSISTANT turns only) and the optional long-term summary is
        carried over, so a restored conversation keeps full context. The fetch
        reads at least twice the window so the window is exact regardless of the
        configured ``CHAT_HISTORY_LIMIT`` (§21.6).
        """
        from ai.core.state import ChatTurn
        from ai.core.state import MessageRole as AIRole

        memory = self._get_memory()
        limit = max(50, memory.chat_history_limit * 2)
        messages = await self._chat_history.get_history(
            conversation_id=conversation.id,
            limit=limit,
        )
        turns: list[Any] = []
        for message in messages:
            if message.role not in _HISTORY_ROLES:
                continue
            role = AIRole.USER if message.role is MessageRole.USER else AIRole.ASSISTANT
            turns.append(ChatTurn(role=role, content=message.content))
        return memory.rebuild(turns, summary=conversation.summary)

    # -- persistence helpers --------------------------------------------------

    async def _persist_citations(
        self,
        *,
        message_id: uuid.UUID,
        citations: list[Any],
    ) -> list[ChatCitationRead]:
        """Persist citations as ``ai_sources`` rows, resolving DB links (§21.4).

        A citation's vector ``chunk_id`` is resolved back to its
        ``knowledge_chunks`` row through ``vector_id``; the resolved row also
        provides the authoritative document link. Unresolved sources are still
        stored with their snapshot fields (title/url/category/snippet/score) so
        the per-message sources endpoint always reflects the answer. Returns the
        citations as they were persisted (with any resolved links) for the
        response envelope.
        """
        reads: list[ChatCitationRead] = []
        for citation in citations:
            knowledge_document_id: uuid.UUID | None = None
            knowledge_chunk_id: uuid.UUID | None = None

            if citation.chunk_id is not None:
                chunk = await self._chunks.get_by_vector_id(citation.chunk_id)
                if chunk is not None:
                    knowledge_chunk_id = chunk.id
                    knowledge_document_id = chunk.knowledge_document_id

            if (
                knowledge_chunk_id is None
                and citation.document_id is not None
                and await self._documents.get_by_id(citation.document_id) is not None
            ):
                knowledge_document_id = citation.document_id

            await self._sources.create_source(
                message_id=message_id,
                source_title=citation.title,
                source_type=SourceType.RAG,
                knowledge_document_id=knowledge_document_id,
                knowledge_chunk_id=knowledge_chunk_id,
                source_url=citation.url,
                category=citation.category,
                relevance_score=citation.relevance_score,
                snippet=citation.snippet,
            )
            reads.append(
                ChatCitationRead(
                    source_title=citation.title,
                    source_url=citation.url,
                    category=citation.category,
                    snippet=citation.snippet,
                    relevance_score=citation.relevance_score,
                    knowledge_document_id=knowledge_document_id,
                    knowledge_chunk_id=knowledge_chunk_id,
                )
            )
        return reads

    # -- mapping helpers ------------------------------------------------------

    @staticmethod
    def _to_ai_agent(agent: AgentKey) -> AIAgentKey:
        from ai.core.state import AgentKey as AIAgentKey

        return AIAgentKey(agent.value)

    @staticmethod
    def _to_handoff(handoff: Any) -> HandoffRead | None:
        if handoff is None:
            return None
        return HandoffRead(
            routed_to=AgentKey(handoff.routed_to.value),
            previous_agent=AgentKey(handoff.previous_agent.value),
            reason=handoff.reason,
        )


__all__ = ["AIChatService"]

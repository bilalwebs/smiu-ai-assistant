"""Conversation memory package (AI_ARCHITECTURE.md §21).

Short- and long-term conversation memory as an explicit service (§1.4.7). The
stateless ``ConversationMemoryManager`` enforces the short-term window (§21.2),
supports opt-in long-term summarization (§21.3), rebuilds session memory from
persisted data (§21.4, §22.5), and never fails a run on a persistence error
(§23.1).
"""

from ai.memory.manager import ConversationMemoryManager, SessionMemory

__all__ = ["ConversationMemoryManager", "SessionMemory"]

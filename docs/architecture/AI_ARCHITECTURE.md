# AI_ARCHITECTURE.md

**Agentic AI-Based University Workflow Automation System**
Multi-Agent Student Support Platform — developed for **Sindh Madressatul Islam University (SMIU)**

> Version: 1.0 · Status: Approved Architecture · Last Updated: August 2026 · Owner: Final Year Project Team
> Scope: Single source of truth for the complete AI architecture — philosophy, multi-agent system, LangGraph workflow, RAG, memory, safety, evaluation, and future expansion.
> Sufficiently detailed that the entire AI service (LangGraph workflow, agents, RAG pipeline, prompts, memory, tools) can be generated without additional architectural instructions.
> This document is **architecture and documentation only** — it contains no Python, no LangGraph code, no SQL, no JSON, no configuration files, and no prompts.

---

## Table of Contents

1. [AI Philosophy](#1-ai-philosophy)
2. [Overall AI Architecture](#2-overall-ai-architecture)
3. [Multi-Agent System](#3-multi-agent-system)
4. [Coordinator Agent](#4-coordinator-agent)
5. [Admission Agent](#5-admission-agent)
6. [Examination Agent](#6-examination-agent)
7. [FAQ Agent](#7-faq-agent)
8. [Future Agents](#8-future-agents)
9. [Agent Routing](#9-agent-routing)
10. [Conversation State](#10-conversation-state)
11. [LangGraph Workflow](#11-langgraph-workflow)
12. [State Management](#12-state-management)
13. [Prompt Strategy](#13-prompt-strategy)
14. [RAG Pipeline](#14-rag-pipeline)
15. [Embedding Pipeline](#15-embedding-pipeline)
16. [Document Retrieval](#16-document-retrieval)
17. [Context Building](#17-context-building)
18. [Response Generation](#18-response-generation)
19. [Citation Generation](#19-citation-generation)
20. [Hallucination Prevention](#20-hallucination-prevention)
21. [Conversation Memory](#21-conversation-memory)
22. [Session Management](#22-session-management)
23. [Error Recovery](#23-error-recovery)
24. [Agent Handoff](#24-agent-handoff)
25. [Safety Rules](#25-safety-rules)
26. [Guardrails](#26-guardrails)
27. [AI Response Formatting](#27-ai-response-formatting)
28. [Confidence Handling](#28-confidence-handling)
29. [Feedback Loop](#29-feedback-loop)
30. [Logging](#30-logging)
31. [Monitoring](#31-monitoring)
32. [Performance Optimization](#32-performance-optimization)
33. [Future AI Improvements](#33-future-ai-improvements)
34. [Prompt Engineering Standards](#34-prompt-engineering-standards)
35. [AI Model Management](#35-ai-model-management)
36. [Knowledge Base Management](#36-knowledge-base-management)
37. [AI Security & Privacy](#37-ai-security--privacy)
38. [AI Evaluation Metrics](#38-ai-evaluation-metrics)

---

## 1. AI Philosophy

### 1.1 Vision

The AI layer transforms how SMIU students interact with the university: instead of a simple chatbot that answers questions, it is an **agentic workflow platform** that routes, processes, and resolves real university workflows end to end (PROJECT_RULES.md). Students ask in natural language; a **Coordinator Agent** detects intent and delegates to specialist agents (Admission, Examination, FAQ) that answer **grounded in the university knowledge base** through **Retrieval-Augmented Generation (RAG)** — never from model memory alone.

### 1.2 Objectives

| # | Objective | Measure |
| - | --------- | ------- |
| 1 | **Grounded, trustworthy answers** | Every answer is supported by retrieved sources; hallucination rate tracked (Section 38) |
| 2 | **Correct routing** | User intents reach the right specialist; routing accuracy measured (Section 38) |
| 3 | **End-to-end workflow resolution** | Conversations escalate into trackable requests when action is needed |
| 4 | **Low-latency, efficient experience** | Streaming responses with a bounded token budget (Section 32) |
| 5 | **Explainable behavior** | Citations, routing decisions, and agent handoffs are visible to the user (ui-ux-design.md §13) |
| 6 | **Extensible agent platform** | New agents added by configuration, not new plumbing (Section 8) |
| 7 | **Research-grade quality** | The architecture itself is an FYP research contribution |

### 1.3 Design Principles

| # | Principle | Meaning |
| - | --------- | ------- |
| 1 | **Single entry point** | All external input enters through the Coordinator Agent; specialists are reached only through the workflow (BACKEND_ARCHITECTURE.md §31.1) |
| 2 | **Always retrieve before answering** | RAG precedes LLM generation whenever knowledge is required (PROJECT_RULES.md AI Behaviour Rules) |
| 3 | **Never hallucinate** | Unavailable information is explicitly identified; the assistant recommends the correct department |
| 4 | **Modular agents** | Each agent owns its prompt, retrieval scope, and tool set; modules are isolated and swappable |
| 5 | **Graph-based control flow** | All orchestration runs through the LangGraph state machine — no ad-hoc agent calls outside the graph |
| 6 | **Typed, structured boundaries** | Inputs, outputs, and state are Pydantic-typed; no free-form plumbing between layers |
| 7 | **Memory as a service** | Short- and long-term memory are explicit components, not incidental prompt stuffing |
| 8 | **Observability by default** | Routing, retrieval, generation, and failures are logged and traceable (Sections 30–31) |
| 9 | **Safety first** | Guardrails, PII protection, and university safety policies apply to every response (Sections 25–26, 37) |

### 1.4 Reliability Goals

| Goal | Target |
| ---- | ------ |
| AI availability | High availability of the AI endpoint; graceful degradation when the LLM is down (Section 23) |
| Grounding reliability | No unsupported factual claim reaches the user (Section 20) |
| Deterministic workflows | State transitions are deterministic; only LLM-generated content varies |
| Bounded failure | A retrieval or model failure never takes down chat; fallback responses always available |
| Reproducibility | Model and prompt versions are pinned and traceable per message (Sections 30, 35) |

### 1.5 Explainability

- **Visible routing:** the active agent and handoffs are surfaced in the UI (ui-ux-design.md §13.4).
- **Citations:** every RAG-grounded answer carries collapsible sources (Section 19).
- **Traceability:** `agent_logs` and `ai_sources` (DATABASE_DESIGN.md §22, §24) persist the routing decision, retrieval, and citations for every run.
- **Correlation IDs:** each request carries a correlation ID linking API, AI, and database logs.

### 1.6 Scalability & Maintainability

- **Stateless AI service:** any number of AI service instances can serve traffic; conversation and memory state live in the database (DATABASE_DESIGN.md).
- **Configuration-driven agents:** agents are registered in the Agent Manager and routing table — no changes to callers.
- **Modular folders:** agents, graphs, rag, prompts, memory, and tools are separate modules (PROJECT_RULES.md folder ownership).
- **Clean architecture:** the AI layer is a first-class boundary consumed only by services (BACKEND_ARCHITECTURE.md §20).

### 1.7 Student-First Approach

- Answers are concise, complete, and explain the next step or university process (PROJECT_RULES.md AI Behaviour Rules).
- The interface streams responses, shows a thinking state, preserves drafts on error, and allows one-click copy and feedback (ui-ux-design.md §31).
- No dead ends: unknown intents yield clarifying or escalation responses, never silence.

---

## 2. Overall AI Architecture

### 2.1 High-Level View

```
Student (Next.js UI)
        │
        ▼
FastAPI Backend (services)
        │  AI integration boundary
        ▼
AI Service — Agent Manager facade
        │
        ▼
LangGraph Workflow (Coordinator as entry node)
        │
        ├── Intent Detection ──► Agent Routing
        │
        ▼
Specialist Agent (Admission / Examination / FAQ)
        │
        ├── RAG Retrieval ──► FAISS vector store (knowledge/vectorstore/)
        │                        ▲
        │                        │  index
        │                 Knowledge ingestion & Embedding pipeline
        │
        ▼
Context Builder ──► LLM (Gemini 2.5 Flash) ──► Structured Response
        │                                              │
        ▼                                              ▼
Citation assembly ───────────────────────────► Response + Sources
        │
        ▼
Memory update ──► ai_conversations / chat_history (PostgreSQL)
        │
        ▼
Return to FastAPI → UI
```

### 2.2 Major Components

| Component | Responsibility | Location / Store |
| --------- | -------------- | ---------------- |
| **Agent Manager** | Registry and lifecycle of agents; facade for the business layer | `ai/core` |
| **Coordinator Agent** | Entry node: intent detection, routing, response aggregation, fallback | `ai/agents/coordinator` |
| **Specialist Agents** | Admission, Examination, FAQ — grounded answers in their domain | `ai/agents/{admission,examination,faq}` |
| **LangGraph Workflow** | State machine: detect → select → retrieve → generate → persist | `ai/graphs` |
| **RAG Pipeline** | Ingestion, retrieval, ranking, context building | `ai/rag` |
| **Embedding Pipeline** | Sentence Transformer embedding generation and index updates | `ai/rag/embeddings` |
| **Vector Store** | FAISS index over the knowledge base | `knowledge/vectorstore/` |
| **Memory Layer** | Short- and long-term conversation memory | `ai/memory` |
| **Prompt Registry** | Versioned prompts owned per agent | `ai/prompts` |
| **Tools** | Typed agent tools (retrieval, formatting; future university APIs) | `ai/tools` |
| **LLM Gateway** | Model-agnostic invocation, config, retry, fallback (Gemini primary) | `ai/core` |
| **Knowledge Base** | Source documents by category + metadata | `knowledge/`, `knowledge_documents`, `knowledge_chunks` |
| **Response Builder** | Final answer assembly, citations, handoff metadata | `ai/core` |
| **Evaluation & Monitoring** | Metrics, logging, tracing (Sections 30–31, 38) | `ai/core`, `agent_logs` |

### 2.3 Interaction Rules

- **Routers never call the AI layer** — only services do (BACKEND_ARCHITECTURE.md §20.2).
- The AI layer never writes application data directly; it persists through the same repositories.
- The LLM provider is behind the **LLM Gateway**; switching primary/fallback requires configuration, not code (Section 35).
- The vector store is a **cache of the knowledge base**, always regenerable from `knowledge/` sources.

---

## 3. Multi-Agent System

### 3.1 Agent Model

The system is a **single LangGraph workflow with one external entry point** (the Coordinator Agent) and a set of **stateless specialist agents**. Agents never call each other directly — all communication flows through shared graph state and the Coordinator (BACKEND_ARCHITECTURE.md §31).

### 3.2 Phase 1 Agents

| Agent | Role | Responsibility |
| ----- | ---- | -------------- |
| **Coordinator** | Entry, router, orchestrator | Intent detection, routing, workflow lifecycle, response aggregation, fallback |
| **Admission** | Specialist | Admission requirements, eligibility, documents, merit, process |
| **Examination** | Specialist | Date sheets, results, admit cards, exam rules, improvement policy |
| **FAQ** | Specialist | General FAQs, departments, office timings, campus info, contacts |

### 3.3 Agent Contracts

Every agent follows the same contract:

| Contract | Detail |
| -------- | ------ |
| **Input** | Typed graph state (query, conversation context, routing decision) |
| **Processing** | Own prompt + own retrieval scope + own tool set |
| **Output** | Typed result written back to graph state (answer, sources, status) |
| **Isolation** | No cross-agent direct calls; no shared mutable modules |

### 3.4 Agent Registry

- Agents are registered in the **Agent Manager** with: key, display name, description (for routing), prompt reference, retrieval scope, and tool set.
- Routing chooses a specialist by the registered metadata — **no hardcoded branches**.
- New agents are added by registry + routing table entries (Section 8), which is the explicit future-scalability path (PROJECT_RULES.md AI Agents).

### 3.5 Coordination Model

```
Coordinator (entry)
   ├─ intent detection
   ├─ route ──► Specialist ──► RAG ──► LLM ──► answer + sources
   │
   ├─ aggregate response
   ├─ memory update
   └─ return to caller
```

---

## 4. Coordinator Agent

### 4.1 Responsibilities

| Responsibility | Detail |
| -------------- | ------- |
| **Entry point** | The only agent that can be entered externally (BACKEND_ARCHITECTURE.md §31.1) |
| **Intent analysis** | Classifies the incoming query (admission, examination, faq, general, out-of-scope) |
| **Routing** | Selects the correct specialist from the Agent Manager registry |
| **Workflow management** | Owns the graph lifecycle: start, route, retrieve, aggregate, persist |
| **Handoff execution** | Transfers the conversation to the specialist and signals the handoff to the UI |
| **Response orchestration** | Combines specialist output, citations, and status into one typed response envelope |
| **Fallback** | Handles ambiguous, low-confidence, or out-of-scope intents with a grounded, clarifying response |

### 4.2 Decision Making

| Decision | Input | Output |
| -------- | ----- | ------ |
| **Intent** | User query + conversation context | Intent label + confidence score |
| **Specialist selection** | Intent label + agent registry metadata | Agent key |
| **Retrieval scope** | Specialist domain | Knowledge categories to query |
| **Escalation** | Action needed vs. answer-only | Answer, or answer + request-conversion suggestion |
| **Fallback** | Confidence threshold / no retrieval results | Clarifying response or "information unavailable" response |

### 4.3 Intent Analysis

- Intent analysis is **structured**: the Coordinator produces a typed routing signal (intent, selected agent, confidence) — never free-form text (PROJECT_RULES.md Prompt Engineering Rules).
- Low-confidence intents are treated as **unknown** and trigger a clarifying response (Section 9.6).
- Intent analysis uses the conversation context, not just the latest message, so follow-ups ("what about the fees?") route correctly.

### 4.4 Routing

- Routing is data-driven via the Agent Manager registry (Section 3.4).
- The routing table maps intents to specialists; priority rules resolve ambiguous intents (Section 9.3).
- The routing decision is logged in `agent_logs` (DATABASE_DESIGN.md §24) and surfaced in the UI handoff chip.

### 4.5 Response Orchestration

- The Coordinator collects the specialist's answer, retrieved citations, and status into a **single typed response envelope**.
- Aggregation normalizes output regardless of which specialist produced it — the caller never branches on agent identity.
- The envelope includes: message text, citations, active agent, handoff metadata, confidence, and completion status.

### 4.6 Fallback Strategy

| Case | Coordinator action |
| ---- | ------------------ |
| Intent undetectable | Returns a clarifying question; no specialist invoked |
| Low confidence | Requests clarification or offers the closest specialist |
| Retrieval failure | Degrades to a best-effort grounded response or an explicit "information unavailable" message with department recommendation |
| Specialist error | Catches, logs, returns a friendly error with a retry signal — the workflow is never left half-executed |
| Out-of-scope query | Responds with scope boundaries and offers escalation/department contact |

---

## 5. Admission Agent

### 5.1 Responsibilities

- Answer admission queries **grounded in the admission knowledge base**.
- Explain admission requirements, eligibility, required documents, merit queries, and the admission process.
- Provide next-step guidance and, when action is needed, support escalation to a trackable request (BACKEND_ARCHITECTURE.md §32.2).

### 5.2 Knowledge Scope

| Area | Sources (knowledge/) |
| ---- | -------------------- |
| Admission requirements | `admission/` guides |
| Eligibility criteria | `admission/` |
| Required documents | `admission/` |
| Merit policy and merit lists | `admission/` |
| Admission process & deadlines | `admission/` + `documents/` |

### 5.3 Supported Queries

| Example query type | Behavior |
| ------------------ | -------- |
| "What are the requirements for BSSE admission?" | Grounded answer with document list |
| "Am I eligible with 60% in intermediate?" | Eligibility explanation grounded in criteria |
| "What documents do I need?" | Check-list answer with citations |
| "When is the admission deadline?" | Dated answer with source |
| "Where is my application in the merit process?" | Routes to request tracking / escalation |

### 5.4 Limitations

- Cannot guarantee admission decisions — official merit outcomes come from the university.
- Individual case evaluation (e.g., specific equivalency) is referred to the Admission Office.
- Stale or superseded admissions cycles are flagged by the knowledge versioning system (Section 36).

---

## 6. Examination Agent

### 6.1 Responsibilities

- Answer examination queries **grounded in the examination knowledge base**.
- Explain date sheets, results, admit cards, examination rules, and improvement policy.
- Support escalation for confirmation/correction needs (BACKEND_ARCHITECTURE.md §32.3).

### 6.2 Knowledge Scope

| Area | Sources (knowledge/) |
| ---- | -------------------- |
| Date sheets | `examination/` |
| Results and result policy | `examination/` + `documents/` |
| Admit cards | `examination/` |
| Examination rules | `examination/` |
| Improvement policy | `examination/` |

### 6.3 Supported Queries

| Example query type | Behavior |
| ------------------ | -------- |
| "When is the mid-term exam?" | Dated answer with source |
| "How do I get my admit card?" | Process answer with steps |
| "What happens if I miss an exam?" | Policy-grounded answer |
| "How does the improvement policy work?" | Rule explanation with citations |
| "My result seems wrong." | Escalation to request tracking |

### 6.4 Limitations

- Individual result changes are handled by the Examination Department, never by the agent.
- Provisional/pre-official data is not invented; only published information is answered.
- Exam-room or integrity-sensitive content is answered within the published policy only.

---

## 7. FAQ Agent

### 7.1 Responsibilities

- Answer general university questions **grounded in the FAQ and general knowledge base**.
- Provide department, office-timing, campus, and contact information.
- Resolve most queries self-service; escalation is the exception (BACKEND_ARCHITECTURE.md §32.4).

### 7.2 Knowledge Scope

| Area | Sources (knowledge/) |
| ---- | -------------------- |
| General university FAQs | `faq/` |
| Departments and services | `faq/` + `documents/` |
| Office timings | `faq/` |
| Campus information | `faq/` |
| Contact information | `faq/` |

### 7.3 Supported Queries

| Example query type | Behavior |
| ------------------ | -------- |
| "What are the university office hours?" | Grounded answer |
| "How do I contact the registrar?" | Contact card answer |
| "Where is the library?" | Campus information answer |
| "What departments does the university have?" | Department list with citations |

### 7.4 Limitations

- General-answer only; domain-specific questions are routed to the Admission/Examination agents or to a department.
- Contact details change — answers always cite the source so staleness is visible.

---

## 8. Future Agents

Future agents are **placeholders only** for the current FYP (PROJECT_RULES.md). They follow the same registration, routing, prompt, and retrieval contracts as Phase 1 agents — added by configuration, not plumbing.

| Future Agent | Domain / Knowledge Scope | Phase |
| ------------ | ------------------------ | ----- |
| **Finance** | Fees, dues, payment plans, refunds | Phase 2 |
| **Registration** | Enrollment, course registration, semester changes | Phase 2 |
| **Scholarship** | Scholarship programs, eligibility, applications | Phase 2 |
| **Hostel** | Hostel rules, allotments, fees, amenities | Phase 3 |
| **Library** | Catalog, borrowing rules, due dates, fines | Phase 3 |
| **HR** | Employee/HR queries (staff-facing) | Phase 3 |
| **IT Support** | Account access, portal issues, technical support | Phase 3 |
| **Transport** | Shuttle routes, schedules, passes | Phase 3/4 |
| **Placement** | Career services, placements, internships | Phase 4 |
| **Research** | Research policies, supervision, publications, ORIC | Phase 4 |

**Registration rules for new agents:**

| Rule | Detail |
| ---- | ------ |
| Registry entry | Agent key, name, description, prompt reference, retrieval scope, tools |
| Routing table entry | New intent labels mapped to the agent key |
| Knowledge category | New `knowledge/` folder + `knowledge_category` scope |
| Enumerations | New `agent_key` / intent enum values via data migration (DATABASE_DESIGN.md §28) |
| No new plumbing | No changes to the workflow, state, or callers (BACKEND_ARCHITECTURE.md §31.8) |

---

## 9. Agent Routing

### 9.1 Intent Detection

| Concern | Architecture |
| ------- | ------------ |
| Scope | The Coordinator analyzes the **current query plus conversation context** |
| Output | Structured routing signal: intent label, selected agent, confidence score |
| Style | Zero/few-shot classification grounded in the Agent Manager registry descriptions |
| Multi-topic | Primary intent selected; secondary intents noted in the routing signal |
| Logging | Routing signal written to `agent_logs` (DATABASE_DESIGN.md §24) |

### 9.2 Routing Logic

| Step | Decision |
| ---- | -------- |
| 1 | Detect intent + confidence from the query and context |
| 2 | Map intent → agent via the routing table |
| 3 | Apply priority rules (Section 9.3) for ambiguous/multi-topic input |
| 4 | Route: handoff the specialist with full graph state |
| 5 | Aggregate the specialist result into the response envelope |

### 9.3 Priority

| Priority | Rule |
| -------- | ---- |
| **Explicit intent** | High-confidence, unambiguous match wins |
| **Domain precedence** | Exam-specific terms (date sheet, result, admit card) beat general FAQ |
| **Action-safety precedence** | Safety-restricted or sensitive topics route to safe handling (Sections 25–26) |
| **Conversation continuity** | Follow-ups inherit the previous agent unless the new intent is explicit |
| **Tie-break** | Lower-confidence match triggers a clarifying question rather than a forced route |

### 9.4 Fallback Routing

| Trigger | Behavior |
| ------- | -------- |
| No intent match | Clarifying response with suggested intents |
| Confidence below threshold | Ask for clarification; optionally offer the nearest specialist |
| Specialist unavailable/error | Coordinator fallback response + retry signal (Section 23) |
| Retrieval empty | "Information unavailable" + department recommendation |

### 9.5 Unknown Intent Handling

- The Coordinator never guesses. Unknown intents produce a **grounded, clarifying response** listing what the assistant can help with.
- Repeated unknown intents suggest escalation to a department or request creation.
- Unknown intents are logged and surfaced in evaluation metrics (Section 38).

### 9.6 Multi-Agent Collaboration

- Phase 1 collaboration is **Coordinator-mediated**: specialists write results to shared state; the Coordinator aggregates.
- Cross-domain questions are decomposed by the Coordinator: primary agent answers; secondary intents are noted and, where needed, answered sequentially via the same workflow.
- Future collaboration (Phase 4+) may introduce a sub-graph pattern within the same single-entry model (Section 33).

---

## 10. Conversation State

### 10.1 Conversation Lifecycle

| Stage | Description | Persistence |
| ----- | ----------- | ----------- |
| **Create** | Conversation initialized (session or new chat) | `ai_conversations` row |
| **Active** | User turns + agent turns accumulate | `chat_history` rows |
| **Handoff** | Agent switch with visible chip; state carries through | `ai_conversations.current_agent` |
| **Idle/Archived** | Inactive for the retention window | `ai_conversations.status` |
| **Restored** | Reopened from history | Re-read from `ai_conversations` + `chat_history` |

### 10.2 State Object

The graph state is a **typed Pydantic object** (the single source of truth during a run, per BACKEND_ARCHITECTURE.md §31.5):

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `user_query` | text | Current user turn |
| `conversation_id` | UUID | Owning conversation |
| `user_context` | typed | Authenticated user info, role, department |
| `message_history` | list | Recent turns (short-term memory window) |
| `routing_signal` | typed | Intent, selected agent, confidence |
| `retrieved_context` | list | Retrieved chunks + metadata |
| `agent_output` | typed | Specialist answer, citations, status |
| `metadata` | dict | Provider data, timings, correlation ID |

### 10.3 Context Variables

| Variable | Source | Used by |
| -------- | ------ | ------- |
| `user_id` | Auth (from FastAPI) | Memory, logging, ownership |
| `user_role` | Auth | Scope and permissions |
| `department` | Student profile | Personalization |
| `conversation_id` | Session | Continuity, persistence |
| `current_agent` | Last handoff | Header identity, UI |
| `locale` | User preference | Formatting (Urdu: future) |

### 10.4 Metadata

- Metadata covers non-queryable auxiliary data: model name/version, token usage, latency, provider call IDs, correlation ID.
- Metadata never contains secrets or raw PII (Section 37).
- Stored in `chat_history.metadata` / `agent_logs` (DATABASE_DESIGN.md).

### 10.5 Session State

- Session state (short-lived, per conversation) is derived from `ai_conversations` and the memory window — never duplicated in another store.
- Restoring a session rebuilds the graph state from the last persisted messages (Section 22).

---

## 11. LangGraph Workflow

### 11.1 Workflow Overview

```
                    ┌────────────────────────────┐
   user turn ──►    │  ENTRY: Coordinator        │
                    │  - intent detection        │
                    └────────────┬───────────────┘
                                 ▼
                    ┌────────────────────────────┐
                    │  ROUTER (edges)            │
                    │  admission │ examination │faq │
                    └────────────┬───────────────┘
                                 ▼
                    ┌────────────────────────────┐
                    │  SPECIALIST AGENT          │
                    │  - retrieval (RAG)        │
                    │  - context building       │
                    │  - generation (LLM)       │
                    └────────────┬───────────────┘
                                 ▼
                    ┌────────────────────────────┐
                    │  RESPONSE BUILDER          │
                    │  - citations               │
                    │  - aggregation             │
                    └────────────┬───────────────┘
                                 ▼
                    ┌────────────────────────────┐
                    │  EXIT: persist memory      │
                    │  - write messages          │
                    │  - write agent_logs        │
                    └────────────┬───────────────┘
                                 ▼
                             return to caller
```

### 11.2 Nodes

| Node | Responsibility |
| ---- | -------------- |
| **Detect Intent** | Classify the query; produce the routing signal |
| **Route** | Select specialist from the routing table (Section 9) |
| **Retrieve** | RAG retrieval scoped to the specialist domain (Section 16) |
| **Build Context** | Assemble history + retrieved context within the token budget (Section 17) |
| **Generate** | LLM invocation producing the grounded answer (Section 18) |
| **Assemble Citations** | Map retrieved chunks to the citation list (Section 19) |
| **Aggregate Response** | Coordinator envelope: answer, citations, handoff, status |
| **Persist** | Write messages, sources, and logs; update counters (DATABASE_DESIGN.md §15–16, §24) |

### 11.3 Edges & State Transitions

| Edge | Condition |
| ---- | --------- |
| Entry → Detect Intent | Every external call |
| Detect Intent → Route | Always |
| Route → Specialist | Routing signal resolves to an agent |
| Route → Clarify (loop) | Confidence below threshold; returns a clarifying turn |
| Specialist → Build Context | Retrieval completed |
| Build Context → Generate | Context assembled |
| Generate → Assemble Citations | Generation completed |
| Assemble Citations → Aggregate | Always |
| Aggregate → Persist | Always |
| Persist → Exit | Always |

### 11.4 Entry Point & Exit Point

- **Entry:** the Coordinator node is the only externally reachable node (BACKEND_ARCHITECTURE.md §31.1).
- **Exit:** the Persist node; every run completes with persisted state, even on degraded paths (fallback responses are persisted as assistant messages).

### 11.5 Loops

| Loop | Purpose | Bounded by |
| ---- | ------- | ---------- |
| **Clarification** | Ask for a clarifying question when intent is ambiguous; the user's next turn re-enters the graph | Max clarification rounds (default 1–2), then fallback routing |
| **Retry (transient)** | Retry LLM/retrieval on transient failure | Bounded backoff retries (Section 23) |
| **Tool feedback** | Tool calls feed results back into the same turn | Single tool-call cycle per turn (Phase 1) |

### 11.6 Termination Conditions

| Condition | Action |
| --------- | ------ |
| Response envelope built and persisted | Normal termination |
| Clarification limit reached | Fallback routing, then termination |
| Max retries exhausted | Fallback response, error logged, termination |
| Safety-restricted intent | Safe response returned, termination |
| User stops streaming (UI) | Partial response retained with "Stopped" state, termination |

---

## 12. State Management

### 12.1 State Persistence

| State | Storage | Lifetime |
| ----- | ------- | -------- |
| Graph state (run) | In-memory during the run; written at defined checkpoints | Single request |
| Conversation state | `ai_conversations` | Retention window (DATABASE_DESIGN.md §35) |
| Messages | `chat_history` | Retention window |
| Agent/routing traces | `agent_logs` | Retention window |
| Citations | `ai_sources` | Retention window |

**Rule:** shared state is the single source of truth **during a run**; it is written to persistent storage only at defined checkpoints (BACKEND_ARCHITECTURE.md §31.5).

### 12.2 Shared State

- All nodes read/write the same typed graph state — there is no out-of-band communication.
- The Coordinator owns conversation context and the routing decision; the RAG layer owns retrieved context; the specialist owns its answer.

### 12.3 Agent State

- Specialist agents are **stateless workers**: they read task input from state, execute, and write results back (BACKEND_ARCHITECTURE.md §31.2).
- No specialist holds cross-request state.

### 12.4 Conversation State

- Conversation state = identity (`ai_conversations`) + ordered messages (`chat_history`).
- Rebuilds of in-run state (history window) are read from the memory layer (Section 21).

### 12.5 Memory Handling

- Short-term memory: recent turns within the window (Section 21.2).
- Long-term memory: summarized conversation state across sessions (Section 21.3).
- Memory is read into context by the **Context Builder**, never appended raw beyond the token budget (Section 17).

---

## 13. Prompt Strategy

### 13.1 Prompt Ownership

- **Every agent owns its prompt** (PROJECT_RULES.md Prompt Engineering Rules).
- Prompts live in `ai/prompts/`, organized per agent and purpose — never hardcoded in routes, graphs, or agents.
- Prompts are treated as versioned assets (Section 34).

### 13.2 Prompt Types

| Type | Owner | Purpose |
| ---- | ----- | ------- |
| **System prompt** | AI service | Global behavior, safety, grounding, formatting rules; applied to all agents |
| **Coordinator prompt** | Coordinator Agent | Intent detection, routing logic, clarification, fallback behavior |
| **Specialist prompt** | Each specialist | Domain knowledge, retrieval scope, supported/unsupported queries, tone |
| **Context-injection template** | RAG pipeline | How retrieved chunks + history are presented to the LLM |
| **Citation/format template** | Response Builder | Structured output and citation assembly guidance |

### 13.3 Prompt Hierarchy

```
System Prompt (global behavior + safety)
    └── Agent Prompt (Coordinator or specialist role)
            └── Context Injection (history + retrieved documents, budgeted)
                    └── Task instruction (current user turn)
```

Lower layers override or extend higher layers only where explicitly designed; safety rules are never overridden.

### 13.4 Composition Rules

- Prompts are **modular and composable**: shared components (formatting, safety, citation style) are reused, never duplicated (PROJECT_RULES.md Reusability).
- Dynamic variables are injected from typed state (user context, retrieved context, history) — never from raw user text that could break structure (Section 26).
- Structured outputs are preferred over free-form text (Section 18).

### 13.5 Context-Aware Prompting

- The context builder assembles history + retrieval within the token budget (Section 17).
- Prompts receive the **current conversation window** and **retrieved evidence**; the LLM is instructed to answer from evidence only (Section 20).

---

## 14. RAG Pipeline

### 14.1 End-to-End Workflow

```
knowledge/ sources
   ▼ ingestion (Section 36)
Chunking → Embedding (Sentence Transformers) → FAISS index
   ▲                                        │
   │                                        ▼
   │                              Student query (retrieval)
   │                                        │
   └───────────────────  retrieved chunks  │
                                          ▼
                            Context Builder (budgeted)
                                          ▼
                            LLM generation (grounded)
                                          ▼
                            Response + Citations
```

### 14.2 Document Ingestion

| Stage | Detail |
| ----- | ------ |
| Validate | File type, size, checksum, category (Section 36) |
| Chunk | Split into retrievable units with metadata (Section 36) |
| Embed | Generate vectors via Sentence Transformers (Section 15) |
| Index | Write to FAISS at `knowledge/vectorstore/` |
| Persist | `knowledge_documents` + `knowledge_chunks` rows |

### 14.3 Retrieval

| Step | Detail |
| ---- | ------ |
| Query embedding | Student query embedded with the same model as the index |
| Similarity search | FAISS search over the index (Section 16) |
| Filtering | Category / metadata filters from the specialist scope |
| Ranking | Score-based ordering with optional re-ranking (Section 16.3) |
| Top-K | Select top chunks within budget (Section 16.5) |

### 14.4 Ranking

- Primary ranking by similarity score.
- Optional cross-encoder re-ranking for precision (Phase 2, Section 33).
- Duplicate/source-collapse handling: deduplicate chunks from the same document when appropriate.

### 14.5 Context Generation

- Retrieved chunks + history assembled by the Context Builder within the token budget (Section 17).
- Source metadata (title, category, snippet) is carried into the response for citations (Section 19).

### 14.6 Response Generation

- The LLM generates the answer **grounded strictly in the provided context** (Section 18).
- If context cannot support the answer, the no-answer policy applies (Section 20.4).

---

## 15. Embedding Pipeline

### 15.1 Embedding Generation

| Concern | Architecture |
| ------- | ------------ |
| Model | **Sentence Transformers** (bilingual-capable encoder) |
| Model parity | The same model must embed queries and documents (fixed at index build time) |
| Batch embedding | Documents embedded in batches; queries embedded individually at request time |
| Dimensionality | Fixed per model; stored consistently in the FAISS index |
| Locality | Embedding runs inside the AI service (or background job) — no external call per chunk |

### 15.2 Embedding Storage

| Store | Contents |
| ----- | -------- |
| FAISS index | Vectors only (`knowledge/vectorstore/`), keyed by `vector_id` |
| `knowledge_chunks` | Chunk text + `vector_id` mapping (DATABASE_DESIGN.md §21.2) |
| Model metadata | Model name + version recorded with the index for reproducibility |

### 15.3 Embedding Updates

- Chunk-level re-embedding on content change; unchanged chunks retain vectors (checksum-driven, Section 36).
- Index rebuild is atomic: build new index → swap reference → delete old (Section 36.7).

### 15.4 Embedding Lifecycle

| Stage | Action |
| ----- | ------ |
| **Create** | New document → chunk → embed → index |
| **Update** | Content changed → re-embed affected chunks → re-index |
| **Delete** | Document removed → remove vectors + chunks |
| **Model upgrade** | Re-embed entire corpus with the new model (scheduled migration, Section 35) |

---

## 16. Document Retrieval

### 16.1 Vector Search

- Query embedded with the same Sentence Transformer as the corpus; FAISS similarity search returns the nearest chunks.
- Index stays in memory (FAISS) for fast local search; PostgreSQL is the metadata source of truth.

### 16.2 Similarity Search

- Similarity measured by the index's distance metric (consistent with the embedding model).
- Only chunks from `is_active = true`, `status = 'processed'` documents are candidates (DATABASE_DESIGN.md §21.3).

### 16.3 Ranking

| Layer | Purpose |
| ----- | ------- |
| **Primary** | Vector similarity score |
| **Secondary (Phase 2)** | Cross-encoder re-ranking for precision |
| **Tie-break** | Source recency / document priority metadata |

### 16.4 Filtering & Metadata Filtering

| Filter | Applied |
| ------ | ------- |
| Category | Specialist scope (admission / examination / faq / documents) |
| Document status | `processed` and `is_active` only |
| Version | Only the current active version of a document |
| Date (future) | Recency windows for time-sensitive queries |

### 16.5 Top-K Retrieval

- `RAG_TOP_K` (default 4) retrieved chunks per query; configurable per agent.
- The Context Builder may further trim to meet the token budget (Section 17).
- Retrieved chunks are always accompanied by source metadata for citation (Section 19).

---

## 17. Context Building

### 17.1 Context Sources

| Source | Role |
| ------ | ---- |
| Conversation history | Short-term memory window (Section 21.2) |
| Retrieved documents | Evidence for grounding (Section 16) |
| User context | Role, department, locale (Section 10.3) |
| System/formatting rules | Global formatting and safety (Section 13) |

### 17.2 Prompt Context Assembly

- History and retrieval are assembled by the **Context Builder** in a defined order: system rules → user context → history window → retrieved evidence → current query.
- Each block is labeled (e.g., history vs. evidence) so the LLM can attribute correctly.
- Retrieved evidence is clearly separated from instruction so the LLM never mistakes instructions in evidence for authority.

### 17.3 Token Budgeting

| Budget | Rule |
| ------ | ---- |
| Global budget | Per-model context window minus a reserved safety margin |
| History cap | `CHAT_HISTORY_LIMIT` turns (default 20) — oldest turns truncated or summarized (Section 21) |
| Retrieval cap | Top-K chunks trimmed by size before injection |
| Priority | Evidence > history > auxiliary metadata when space is tight |
| Over-budget | Chunks trimmed from the lowest-ranked; a retry may widen the budget within limits |

### 17.4 Context Prioritization

1. System safety/format rules (never trimmed).
2. Retrieved evidence (highest score first).
3. Recent conversation turns.
4. Summarized older history.
5. User context metadata (minimal).

---

## 18. Response Generation

### 18.1 Response Workflow

```
Context (history + evidence + rules)
   ▼
LLM invocation (Gemini 2.5 Flash, structured output)
   ▼
Parsed answer + optional structured fields
   ▼
Formatting pass (markdown rules, Section 27)
   ▼
Citation attachment (Section 19)
   ▼
Post-processing validation (Section 18.4)
   ▼
Final response envelope
```

### 18.2 LLM Invocation

- Invoked exclusively through the **LLM Gateway** (Section 35): model selection, config, retries, fallback.
- Structured output: the LLM returns a typed result (answer + optional structured fields), not free-form text alone.
- Generation is bounded by timeouts and retry policy (Sections 23, 35).

### 18.3 Formatting

- The formatting pass applies the AI response formatting rules (Section 27): paragraphs, lists, tables, markdown, code, citations.
- The frontend renders markdown safely; no raw HTML is generated.

### 18.4 Post-Processing

| Check | Action |
| ----- | ------ |
| Grounding validation | Answer references only provided evidence; otherwise no-answer policy (Section 20) |
| Safety filter | Guardrail scan on output (Section 26) |
| Citation completeness | Every factual claim maps to a citation where evidence exists |
| Format compliance | Output conforms to the markdown spec (Section 27) |

---

## 19. Citation Generation

### 19.1 Source Attribution

- Each retrieved chunk carries source metadata (title, category, snippet, score, document id) through the pipeline.
- The Response Builder attaches citations to the answer wherever evidence was used.
- Sources are stored per message in `ai_sources` (DATABASE_DESIGN.md §22).

### 19.2 Citation Formatting

| Rule | Detail |
| ---- | ------ |
| Display | Collapsible "Sources: N" under the AI message (ui-ux-design.md §13.2) |
| Content | Source title + link/path per source |
| Rendering | Markdown-safe; never raw HTML |

### 19.3 Multiple Sources

- Multiple sources are listed in score order (highest first).
- Duplicate chunk citations are de-duplicated (one citation per chunk per message — partial unique constraint in DATABASE_DESIGN.md §22.2).

### 19.4 Confidence Association

- Each source carries its retrieval score.
- Citations may be annotated with a confidence level; low-confidence sources are either deprioritized or surfaced with a caveat (Section 28).

---

## 20. Hallucination Prevention

### 20.1 Grounding

- **Always retrieve before answering** (PROJECT_RULES.md AI Behaviour Rules).
- The LLM is instructed to answer **only from the provided evidence**; generated content outside evidence is rejected.
- System rules and context injection make "answer from evidence only" a hard, non-overridable constraint (Section 13.3).

### 20.2 Confidence Checks

- Retrieval confidence: low top-K scores signal weak grounding → no-answer or clarification path (Section 28).
- Generation confidence: post-processing flags answers lacking source support.

### 20.3 Source Validation

| Check | Detail |
| ----- | ------ |
| Candidate eligibility | Only `processed` + `is_active` documents (Section 16.4) |
| Version currency | Current version only; superseded docs excluded |
| Content match | Answer statements traceable to a retrieved chunk |
| Staleness | Date-bound answers carry their source version (Section 36) |

### 20.4 Unknown Answer Strategy

- If no evidence supports the answer, the assistant says **"information unavailable"** clearly and recommends the correct department (PROJECT_RULES.md AI Behaviour Rules).
- The assistant never guesses, speculates, or fabricates policy.

### 20.5 Retrieval Verification

- Retrieval runs are logged (timing, scores, chunk ids) in `agent_logs`.
- Retrieval relevance is measured continuously (Section 38) and fed back into chunking/ranking tuning.

---

## 21. Conversation Memory

### 21.1 Memory Model

| Memory type | Lifetime | Storage |
| ----------- | -------- | ------- |
| **Short-term** | Current conversation window | `chat_history` (in-window turns) |
| **Long-term** | Across sessions | Summaries derived from `chat_history` |
| **Session** | Per active conversation | `ai_conversations` + memory window |

### 21.2 Short-Term Memory

- Holds the recent `CHAT_HISTORY_LIMIT` turns (default 20) injected into context.
- Preserves continuity for follow-ups and multi-turn requests.
- Oldest turns beyond the window are summarized rather than dropped wholesale when long-term memory is enabled.

### 21.3 Long-Term Memory

- Conversation summaries are generated at conversation milestones (e.g., on archiving) and stored as derived records.
- On restore, the summary plus the recent window reconstructs context (Section 22.5).
- Long-term memory is opt-in for research/consent purposes per the retention policy (DATABASE_DESIGN.md §35).

### 21.4 Session Memory

- Session memory is rebuilt from persisted data at session start — it is never held only in-process.
- The AI service is stateless; any instance can serve any conversation (Section 1.6).

### 21.5 Persistent History

- Every message is persisted in `chat_history` at the Persist node (Section 11.2).
- History drives the UI (conversation sidebar, resume/delete) and the memory layer.

### 21.6 Memory Limits

| Limit | Value / rule |
| ----- | ------------ |
| Window turns | `CHAT_HISTORY_LIMIT` (default 20) |
| Token cap | History budget within the global context budget (Section 17.3) |
| Retention | Per DATABASE_DESIGN.md §35 (2 years active / 5 archived) |
| Content limits | Messages truncated by provider/content limits; never partial context silently |

---

## 22. Session Management

### 22.1 Conversation Lifecycle (session)

```
Session created (new chat) ──► Active (turns accumulate) ──► Idle/expiry ──► Archived ──► Restored
```

### 22.2 Session Creation

- A session = an `ai_conversations` row; created on first user message (or explicitly via "New Chat").
- Auth session (auth/sessions) is separate from the AI conversation (DATABASE_DESIGN.md §25).

### 22.3 Session Updates

- Each turn updates `ai_conversations.last_message_at`, `message_count`, `total_tokens`, and `current_agent` in the same transaction as message writes (Section 34.3 of DATABASE_DESIGN.md).

### 22.4 Session Expiration

- Conversations idle past the inactivity threshold transition to `archived` by a scheduled job (retention policy, Section 35 of DATABASE_DESIGN.md).
- Expired auth sessions force re-authentication; the conversation remains restorable (ui-ux-design.md §33 session expiration).

### 22.5 Session Restoration

- Restoring a conversation rebuilds graph state from persisted history (recent window + summary).
- The UI resumes streaming history; the active agent header reflects the last handoff.

---

## 23. Error Recovery

### 23.1 Failure Matrix

| Failure | Detection | Recovery |
| ------- | --------- | -------- |
| **LLM unavailable** | Gateway timeout/5xx | Bounded retries → fallback model → friendly error + retry option |
| **LLM timeout** | Per-call timeout | Retry once; then "taking too long" state with partial response if any |
| **Retrieval failure** | Index/search error | Best-effort grounded response or explicit "information unavailable" + department recommendation |
| **Agent error** | Specialist exception | Coordinator catches, logs, returns friendly error with retry signal |
| **Rate limit (429)** | Provider response | Bounded backoff retry; friendly rate-limit notice with countdown (ui-ux-design.md §36) |
| **Memory persistence failure** | DB write error | Run completes and returns to caller; persistence retried by background handling |
| **Context overflow** | Token budget exceeded | Trim lowest-priority context and retry (Section 17.3) |

### 23.2 Fallback Responses

- Every failure path terminates with a **visible, friendly state** (ui-ux-design.md §36): inline error + Retry chip, draft preserved.
- Fallback answers never fabricate content; they state unavailability and suggest next steps.

### 23.3 Retry Strategies

| Strategy | Policy |
| -------- | ------ |
| Bounded backoff | Exponential backoff with max retries (default 2) |
| Idempotency | Retried operations are safe to repeat (message write idempotence via message id) |
| Retry gating | External (LLM) retries only for transient errors; never for validation errors |
| Circuit behavior | Sustained failures mark the LLM as degraded; fallback model used (Section 35) |

---

## 24. Agent Handoff

### 24.1 Coordinator Handoff

- A handoff occurs when the Coordinator routes to a specialist — **always explicit and visible** (BACKEND_ARCHITECTURE.md §31.4).
- Represented as a divider chip in the UI: "Routed to Examination Agent →" (ui-ux-design.md §13.4).

### 24.2 Agent Switching

| Trigger | Example |
| ------- | ------- |
| New explicit intent | Student switches from admission to exam questions |
| Follow-up re-route | Follow-up changes topic clearly |
| Clarification resolution | Ambiguous intent resolved to a specialist |

### 24.3 Context Transfer

- The **full graph state** carries through the transition — no context is lost during handoff.
- The routing signal records the old and new agent; the conversation header reflects the active agent.

### 24.4 State Synchronization

- Handoffs update `ai_conversations.current_agent` transactionally with the turn.
- The response envelope includes handoff metadata consumed by the UI.
- `agent_logs` records the routing decision for the handoff (DATABASE_DESIGN.md §24).

---

## 25. Safety Rules

### 25.1 University-Specific Safety Policies

| Policy | Rule |
| ------ | ---- |
| **Grounding** | Answers come only from the indexed university knowledge base; nothing invented |
| **Scope** | Responses limited to the platform's scope (admissions, examinations, FAQs) |
| **Official status** | The assistant is never presented as an official university authority; it recommends official channels |
| **Restricted topics** | Financial/legal/medical/immigration advice is outside scope and referred |
| **Exam integrity** | The assistant never helps with cheating, leaks, or unauthorized exam content |
| **Harassment/hate** | Blocked by guardrails (Section 26) |
| **Confidentiality** | Student-specific data is never shared across accounts (Section 37) |

### 25.2 Restricted Topics

| Topic | Handling |
| ----- | -------- |
| Academic misconduct / cheating assistance | Refuse + refer to examination policy |
| Personal data of others | Refuse (access control, Section 37) |
| Legal, medical, financial advice | Scope boundary + department referral |
| Misinformation about the university | Grounded correction from the knowledge base or "information unavailable" |

### 25.3 Safe Responses

- Every response ends with a clear next step or the appropriate department contact when relevant.
- Responses maintain a **professional, neutral, student-first tone** (PROJECT_RULES.md AI Behaviour Rules).

### 25.4 Ethical AI Principles

| Principle | Commitment |
| --------- | ---------- |
| **Beneficence** | The platform serves students' genuine needs, never manipulates |
| **Non-maleficence** | No harmful, misleading, or unsafe content |
| **Transparency** | Citations and routing decisions are visible |
| **Accountability** | Every response is logged and traceable |
| **Fairness** | Equal treatment across students; no bias in routing |
| **Privacy** | Data minimized, anonymized, consent-respecting (Section 37) |

---

## 26. Guardrails

### 26.1 Prompt Injection Prevention

| Control | Architecture |
| ------- | ------------ |
| Input isolation | User content is treated as **data**, never as instructions; dynamic variables are injected in delimited, non-executable blocks |
| Delimiter hygiene | Context blocks are clearly delimited; instructions in evidence are ignored by design |
| Instruction-hierarchy | System rules outrank any injected content (Section 13.3) |
| Input sanitization | Suspicious patterns (instruction-like payloads) detected at the boundary |

### 26.2 Jailbreak Prevention

- Persistent system rules that cannot be overridden by user or evidence content.
- Detection of jailbreak/role-play/authority-invocation attempts → safe refusal or re-grounding.
- Guardrail checks applied to **both input and output**.

### 26.3 Unsafe Prompt Handling

| Detection | Handling |
| --------- | -------- |
| Injection attempt | Ignore embedded instructions; answer only from legitimate context |
| Unsafe request (hate, harassment, cheating) | Refuse with a safe, professional response |
| Out-of-scope request | Scope boundary + department referral |

### 26.4 Output Filtering

- Post-processing scans generated output before delivery (Section 18.4).
- Blocked output is replaced with a safe fallback message; the event is logged.
- Markdown rendering is sanitized client-side (no raw HTML) per ui-ux-design.md §13.2.

### 26.5 Content Moderation

- Lightweight moderation applies to user input and AI output (harmful/offensive content).
- Repeated violations trigger escalation to university administrators (audit trail in `audit_logs`).

---

## 27. AI Response Formatting

The AI response formatting rules follow **ui-ux-design.md §14** exactly:

| Rule | Requirement |
| ---- | ----------- |
| Short paragraphs | Concise, readable; avoid large text blocks |
| Bullet points | Use bullets when presenting multiple items |
| Numbered steps | Use numbered lists for procedures/instructions |
| Bold highlights | Bold key information only when necessary |
| Tables | Only for structured comparisons or data |
| Markdown | Preserve proper markdown for headings, lists, tables, links, code |
| Readability | Well-structured, visually organized |
| Avoid walls of text | Never long, unformatted paragraphs |

### 27.1 Code Formatting

- Code blocks use monospace, dark styling with a copy button and language label (ui-ux-design.md §13.2).
- Code appears only when genuinely relevant to the query (rare in this platform's scope).

### 27.2 Citation Rendering

- Citations render as **collapsible "Sources: N"** under the AI message (Section 19).
- Links open in a new tab safely; sources are never raw HTML.

### 27.3 Formatting Enforcement

- The formatting pass (Section 18.3) enforces these rules after generation.
- The UI renders markdown safely; streaming shows a caret until complete (ui-ux-design.md §36).

---

## 28. Confidence Handling

### 28.1 Confidence Estimation

| Signal | Source |
| ------ | ------ |
| Retrieval scores | Vector similarity of top chunks (Section 16) |
| Intent confidence | Routing signal from the Coordinator (Section 9) |
| Source coverage | Whether evidence supports the claim (Section 20) |
| Answer validation | Post-processing grounding check (Section 18.4) |

### 28.2 Low Confidence Behavior

| Condition | Behavior |
| --------- | -------- |
| Low intent confidence | Clarifying question before routing (Section 9.5) |
| Weak retrieval scores | "Information unavailable" or partial answer with caveat |
| Unsupported claim detected | No-answer policy; department recommendation |

### 28.3 No-Answer Policy

- The assistant **never answers without evidence**.
- No-answer responses state unavailability clearly and recommend the correct department (PROJECT_RULES.md AI Behaviour Rules).

### 28.4 Fallback Strategy (confidence)

- Fallback follows the same matrix as error recovery (Section 23.1): clarify → retrieve narrower → no-answer with referral.
- Low-confidence answers are never presented as definitive.

---

## 29. Feedback Loop

### 29.1 User Feedback

- Students rate AI responses (thumbs up/down or 1–5) and may add comments/flags (ui-ux-design.md §13.2).
- Feedback is persisted in `feedback` (DATABASE_DESIGN.md §23) linked to the message.

### 29.2 Response Rating

| Dimension | Captured |
| --------- | -------- |
| Rating | 1–5 / binary thumbs |
| Comment | Free text |
| Flag | Issue classification (wrong info, hallucination, off-topic) |

### 29.3 Learning Improvements

- Feedback is triaged (`feedback_status`): resolved issues feed prompt/context/retrieval fixes.
- Recurring flagged topics trigger knowledge-base updates (Section 36) or routing tuning (Section 9).
- Evaluation metrics (Section 38) aggregate feedback into quality trends.

### 29.4 Continuous Evaluation

- A periodic evaluation loop samples conversations, applies the metric framework (Section 38), and produces improvement tickets.
- Improvements land in prompts (versioned, Section 34), retrieval config, or knowledge updates — each traceable to the triggering feedback.

---

## 30. Logging

### 30.1 Log Categories

| Category | Events | Store |
| -------- | ------ | ----- |
| **AI logs** | Model, tokens, latency, structured outputs | `agent_logs` / app logs |
| **Conversation logs** | Conversation/message lifecycle | `ai_conversations`, `chat_history` |
| **Routing logs** | Intent, selected agent, confidence, handoff | `agent_logs` |
| **Error logs** | Failures, retries, fallbacks, timeouts | `agent_logs` + app logs |
| **Performance logs** | Latency, token usage, cache hits | app logs / metrics |
| **Audit logging** | Guardrail blocks, security events, PII events | `audit_logs` (DATABASE_DESIGN.md §24) |

### 30.2 Logging Rules

| Rule | Detail |
| ---- | ------ |
| Never log secrets | No API keys, tokens, passwords, or raw refresh tokens (PROJECT_RULES.md) |
| Never log PII | Personal data redacted; user references use ids |
| Correlation | Every log carries the correlation ID for cross-service tracing |
| Structured | Machine-parseable, level-based logs (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| Grounding traces | Retrieval runs, scores, and chunk ids recorded in `agent_logs` |
| Retention | Per DATABASE_DESIGN.md §35 (agent logs 2y, audit 7y+) |

---

## 31. Monitoring

### 31.1 System Health

- Health endpoint reports the AI service status: vector store reachable, LLM gateway reachable, model load.
- Degraded states (LLM down, index missing) surfaced to operators and produce fallback behavior.

### 31.2 Latency

| Metric | Tracked |
| ------ | ------- |
| End-to-end response time | Request → response |
| Node latencies | Detection, retrieval, generation |
| Streaming TTFT | Time to first token |
| 95th/99th percentiles | Latency distribution |

### 31.3 Token Usage

- Tokens per message, per conversation, per agent, per model.
- Cost and quota tracking drive model/retrieval optimization (Section 32).

### 31.4 Agent Monitoring

- Routing distribution, per-agent latency, per-agent error rate, handoff counts.
- Dead/overloaded agents flagged for tuning.

### 31.5 Failure Monitoring

- Error rate, retry rate, fallback rate, timeout rate per node and per agent.
- Alerting thresholds on sustained degradation (Section 23).

### 31.6 Usage Analytics

- Active conversations, queries per day, top intents, peak load.
- Anonymous, aggregated; no individual PII (Section 37).

---

## 32. Performance Optimization

### 32.1 Prompt Optimization

- Concise, modular prompts reduce input tokens (Section 34).
- Prompt versions A/B-tested against evaluation metrics (Section 38).

### 32.2 Retrieval Optimization

| Technique | Benefit |
| --------- | ------- |
| Metadata filtering | Narrower search, faster and more relevant |
| Top-K tuning | Fewer chunks injected, cheaper generation |
| Re-ranking (Phase 2) | Higher precision per retrieved chunk |
| Index in memory | Low-latency FAISS search |

### 32.3 Caching

| Cache target | Strategy |
| ------------ | -------- |
| Retrieval results | Cache frequent query embeddings + results (short TTL) |
| Document/embedding vectors | Build-time cache; no per-request embedding for ingestion |
| Static metadata | Departments, categories, routing table (hot reads) |
| Invalidation | Version/checksum-driven; never stale (Section 36) |

### 32.4 Latency Reduction

| Technique | Effect |
| --------- | ------ |
| Streaming generation | Perceived latency lower; TTFT visible |
| Parallel independent calls | Detection + retrieval where safe |
| Lazy model initialization | No cold-start on warm traffic |
| Bounded context | Smaller generation context → faster tokens |

### 32.5 Token Optimization

- Budget context (Section 17.3); summarize old history instead of dropping (Section 21.2).
- Structured compact outputs; no verbose filler.
- Cache system/static prompt prefixes where supported.

### 32.6 Scalability

- Stateless AI service instances scale horizontally behind the load balancer (Section 1.6).
- FAISS index replicated/read-shared across instances; PostgreSQL is the source of truth.
- Backpressure and concurrency limits protect the LLM and DB under load.

---

## 33. Future AI Improvements

### 33.1 Roadmap

| Phase | Capability |
| ----- | ---------- |
| **Phase 2** | Finance, Registration, Scholarship agents; cross-encoder re-ranking; evaluation harness |
| **Phase 3** | Hostel, Library, HR, IT Support agents; long-term memory; permission-level routing |
| **Phase 4** | Transport, Placement, Research agents; pgvector; knowledge graph; multilingual (Urdu); voice; multimodal |

### 33.2 Additional Agents

- New agents follow the registry + routing contract (Sections 3, 8) with **no changes to the workflow or callers** (BACKEND_ARCHITECTURE.md §31.8).

### 33.3 Voice Support

- Speech-to-text front-end + text-to-speech output; the agent workflow is unchanged (audio ↔ text at the boundary).

### 33.4 Multimodal AI

- Image understanding (scanned documents, merit lists) routed through a vision-capable model within the same grounding rules.

### 33.5 Image Understanding

- Documents, admit cards, and charts as query attachments; vision input is treated as evidence with the same citation/grounding rules.

### 33.6 Fine-Tuning Readiness

- The prompt layer is structured so curated Q&A pairs can later fine-tune a model without changing the architecture (Section 35.7).

### 33.7 Knowledge Graph Integration

- Entities (programs, departments, policies, deadlines) modeled as a graph over the knowledge base for richer retrieval and inference (Phase 4).

### 33.8 Multi-Language Support

- Bilingual embeddings + locale-aware prompts (Urdu); response language follows user `locale` (Section 10.3).

---

## 34. Prompt Engineering Standards

### 34.1 Overview

Prompts are **versioned assets**, owned per agent, composed from shared components, and stored exclusively in `ai/prompts/` (PROJECT_RULES.md Prompt Engineering Rules). This section defines the architecture for prompt creation, composition, versioning, and maintenance — **not** the prompt text.

### 34.2 System Prompts

| Concern | Architecture |
| ------- | ------------ |
| Purpose | Global behavior: safety, grounding, formatting, tone, scope |
| Ownership | AI service core |
| Scope | Applied to every agent run |
| Immutability | Never overridden by agent or user content (Section 13.3) |

### 34.3 Agent Prompts

| Concern | Architecture |
| ------- | ------------ |
| Purpose | Per-agent role: domain, retrieval scope, supported/unsupported queries |
| Ownership | Each agent owns its prompt (PROJECT_RULES.md) |
| Composition | Shared components (safety, formatting) + agent-specific role block |
| Boundary | Agent prompts never contain routing logic (Coordinator-owned) or RAG mechanics (pipeline-owned) |

### 34.4 Dynamic Prompt Templates

| Concern | Architecture |
| ------- | ------------ |
| Parameters | Typed variables (user context, history window, retrieved evidence) injected from graph state |
| Injection safety | Variables are delimited, non-executable data blocks (Section 26.1) |
| Rendering | Template rendering produces the final prompt per run |
| Validation | Required variables validated before invocation |

### 34.5 Context Injection Rules

| Rule | Detail |
| ---- | ------ |
| Order | System rules → user context → history → evidence → query (Section 17.2) |
| Budgeting | Token-budgeted before injection (Section 17.3) |
| Labeling | Blocks labeled for correct attribution |
| No instruction in data | Evidence/history never carries instruction authority (Section 26.1) |

### 34.6 Prompt Versioning

| Concern | Architecture |
| ------- | ------------ |
| Version id | Every prompt has a version id recorded with each generated message |
| Change process | Prompt edits are code-reviewed; old versions remain queryable |
| Traceability | Version + model recorded in `chat_history.metadata` / `agent_logs` for reproducibility |
| Rollback | Previous version restorable without code change |

### 34.7 Prompt Reusability

- Shared components (safety, formatting, citation style, scope boundaries) are defined **once** and composed across agents.
- New agents reuse the shared components rather than duplicating text (PROJECT_RULES.md Reusability).

### 34.8 Prompt Maintenance Strategy

| Practice | Detail |
| -------- | ------ |
| Single source | `ai/prompts/` only; no prompts in routes, graphs, or services |
| Evaluation-driven | Changes justified by evaluation metrics or feedback (Sections 29, 38) |
| Regression check | Prompt changes run through the evaluation harness before merge |
| Drift control | Periodic prompt audits against the current knowledge scope |
| Modularity | Small, composable prompts over one large block (PROJECT_RULES.md) |

**Scalability:** because prompts are modular, versioned, and registry-driven, adding agents or models never requires rewriting prompts — only composing shared components and registering new ones.

---

## 35. AI Model Management

### 35.1 Gemini Model Selection

| Concern | Architecture |
| ------- | ------------ |
| Primary model | **Google Gemini 2.5 Flash** (fast, cost-efficient, strong grounding) |
| Selection criteria | Grounding quality, latency, token economics, availability |
| Model abstraction | All model access through the **LLM Gateway** — services never reference a provider directly |

### 35.2 Model Configuration

| Setting | Policy |
| ------- | ------ |
| Model id/version | Config-driven, recorded per message for traceability |
| Parameters | Per-task profiles (chat vs. classification vs. summarization) |
| Structured output | Schema-driven generation enforced by the gateway |
| Environment | Model and params set via configuration, never hardcoded (Section 7 of BACKEND_ARCHITECTURE.md) |

### 35.3 Temperature Strategy

| Task | Temperature |
| ---- | ----------- |
| Retrieval-grounded answer | Low (factual, deterministic) |
| Intent classification / routing | Low (stable labels) |
| Summarization | Low–moderate |
| Creative/optional content | Moderate (rare in this platform) |

Temperature is set per task profile in the gateway; the default favors **factuality over variety** (Section 20).

### 35.4 Max Token Strategy

| Concern | Policy |
| ------- | ------ |
| Response cap | Per-task max output tokens; bounded by context budget (Section 17.3) |
| Context cap | Global budget = model window minus safety margin |
| Overflow | Trim lowest-priority context and retry (Section 17.3) |

### 35.5 Retry Policy

| Scenario | Policy |
| -------- | ------ |
| Transient errors | Bounded exponential backoff (max 2 retries) |
| Rate limits (429) | Backoff + friendly rate-limit notice (Section 23) |
| Validation errors | No retry — fix input |
| Sustained failure | Circuit degradation → fallback model (Section 35.6) |

### 35.6 Fallback Strategy

| Trigger | Behavior |
| ------- | -------- |
| Primary unavailable | Fallback model used transparently (same gateway contract) |
| Primary rate-limited | Fallback after bounded backoff |
| Persistent degradation | Fallback until primary recovers; status surfaced to monitoring (Section 31) |

Fallback selection is **configuration-driven**; the architecture is model-agnostic (BACKEND_ARCHITECTURE.md §20.2).

### 35.7 Model Versioning & Replacement

| Concern | Policy |
| ------- | ------ |
| Version pinning | Model version recorded per message for reproducibility |
| Upgrade path | New model behind the same gateway interface; A/B tested on the evaluation harness |
| Embedding model changes | Full corpus re-embedding migration (Section 15.4) |
| Fine-tuning readiness | Structured prompt/output layer enables future fine-tuning without architectural change (Section 33.6) |
| Zero plumbing | Model replacement requires configuration + evaluation — no service, graph, or prompt changes |

**Model replacement guarantee:** because the LLM Gateway abstracts the provider, temperature, retries, structured output, and versioning, any model (Gemini, fallback provider, future fine-tuned model) can replace the primary without affecting the rest of the architecture.

---

## 36. Knowledge Base Management

### 36.1 Document Lifecycle

```
Ingest → Validate → Chunk → Embed → Index → Serve (active) → Version/Archive → Retire
```

### 36.2 Document Ingestion

| Stage | Detail |
| ----- | ------ |
| Source | `knowledge/` category folders (admission, examination, faq, documents) |
| Trigger | Manual upload, repository change, or scheduled sync |
| Pipeline | Read → extract text → validate → chunk → embed → index (background job, Section 19 of BACKEND_ARCHITECTURE.md) |

### 36.3 Document Validation

| Check | Detail |
| ----- | ------ |
| File type/size | Whitelist (pdf, md, txt, docx) + size limits |
| Checksum | SHA-256 to detect changes (`knowledge_documents.checksum_sha256`) |
| Content scan | Extractable text present; no binary-only files |
| Category | Must map to a knowledge category |

### 36.4 Document Chunking Strategy

| Concern | Strategy |
| ------- | -------- |
| Chunk unit | Semantic/size-bounded chunks with metadata (source, heading, page) |
| Overlap | Small overlap preserves context across boundaries |
| Determinism | Chunk boundaries reproducible (same input → same chunks) |
| Metadata | Heading, page, section stored per chunk (DATABASE_DESIGN.md §21.2) |
| Storage | `knowledge_chunks` rows + FAISS vectors |

### 36.5 Metadata Structure

| Field | Source |
| ----- | ------ |
| Title, category | Document header / folder |
| Source path | `knowledge/` relative path |
| Version | Document version |
| Checksum | Content hash |
| Author/owner | Uploading department |
| Chunk fields | Heading, page, token/character counts |

### 36.6 Embedding Updates

- Content change (new checksum) → re-embed affected chunks → re-index.
- Unchanged chunks retain vectors; index swap is atomic (Section 15.3).

### 36.7 Version Control & Re-Indexing Policy

| Concern | Policy |
| ------- | ------ |
| Versioning | Each document carries a version; only the current active version is retrieved |
| Re-index trigger | Content change (checksum), metadata change, or manual admin request |
| Atomic swap | Build new index → swap reference → remove old (no retrieval window) |
| Idempotency | Re-indexing is safe to re-run; unchanged documents skipped |
| Regenerability | The FAISS index is always rebuildable from `knowledge/` + `knowledge_chunks` — it is a cache, never the only store |

### 36.8 Knowledge Update Workflow

| Step | Actor |
| ---- | ----- |
| Propose update | Admin / feedback-driven (Section 29) |
| Validate | File + content checks (Section 36.3) |
| Approve | Admin review |
| Ingest | Background pipeline (chunk → embed → index) |
| Publish | New version becomes active; old version archived |

### 36.9 Archive Strategy

- Superseded versions soft-deleted and archived (DATABASE_DESIGN.md §35 — 2 superseded versions retained).
- Retired documents no longer participate in retrieval; `ai_sources` citations remain as snapshots.
- Archive is scheduled, configurable, and audited.

---

## 37. AI Security & Privacy

### 37.1 Prompt Injection Prevention

| Control | Architecture |
| ------- | ------------ |
| Data vs. instruction | User content is never treated as instructions (Section 26.1) |
| Delimited injection | Dynamic variables isolated in non-executable blocks |
| Instruction hierarchy | System rules dominate (Section 13.3) |
| Boundary detection | Suspicious payload patterns screened at input |

### 37.2 Jailbreak Prevention

- Persistent, non-overridable safety rules.
- Detection of authority/roleplay attacks → safe refusal or re-grounding.
- Guardrails applied to input and output (Section 26).

### 37.3 Data Privacy

| Principle | Commitment |
| --------- | ---------- |
| Data minimization | Only the data needed to answer is retrieved/retained |
| Purpose limitation | Data used solely for the student support platform |
| Consent | Long-term retention and research use are consent-based (Section 35 of DATABASE_DESIGN.md) |
| Anonymization | Research corpora de-identified |

### 37.4 PII Handling

| Rule | Detail |
| ---- | ------ |
| Never logged | PII excluded from logs, traces, and `agent_logs` (Section 30) |
| Scoped retrieval | Retrieval never surfaces another user's data |
| Redaction | Account PII scrubbed on soft-delete/anonymization (Section 35.3 of DATABASE_DESIGN.md) |
| In-context | Only the authenticated user's own context is injected (Section 37.6) |

### 37.5 Secure Context Retrieval

- Retrieved context comes **only** from the university knowledge base (public/policy documents).
- Retrieval scope is fixed by category; never parameterized by user-supplied targets.
- Knowledge source access is admin-controlled (Section 36.8).

### 37.6 Access Control

| Concern | Architecture |
| ------- | ------------ |
| User scope | Graph state carries authenticated `user_id`/`role` from FastAPI (Section 10.3) |
| Row-level ownership | Repositories scope by user context (BACKEND_ARCHITECTURE.md §10.2) |
| Role-based routes | AI access goes through protected services |
| No cross-account leakage | A user can never query another user's data via chat |

### 37.7 Sensitive Data Filtering

- Output scanning removes/refuses sensitive personal data from other accounts.
- Knowledge responses stay within the published university corpus.
- Guardrail blocks are logged to `audit_logs` (DATABASE_DESIGN.md §24).

### 37.8 Confidential Information Protection

- Internal/unpublished university information is excluded from retrieval (only published docs indexed).
- Restricted topics (Section 25.2) are refused, not evaded.
- Model calls are configured to minimize retention; API keys in environment only (PROJECT_RULES.md).

### 37.9 Secure Logging

- No secrets, API keys, tokens, or raw PII in logs (Sections 30, 7.3 of BACKEND_ARCHITECTURE.md).
- Structured logs with correlation IDs; sensitive fields redacted before logging.

### 37.10 Responsible AI Guidelines

- Human-in-the-loop for admin actions (knowledge updates, flag resolution).
- Bias and fairness checks in routing/evaluation (Section 25.4, 38).
- Transparency via citations, routing visibility, and feedback loops.
- Continuous monitoring of safety metrics (guardrail block rate, injection attempts).

---

## 38. AI Evaluation Metrics

### 38.1 Metric Framework

| Metric | Definition | Target / Trend |
| ------ | ---------- | -------------- |
| **Retrieval Accuracy** | Retrieved chunks relevant to the query (ground-truth sampled) | High; tracked per category |
| **Response Accuracy** | Answer factually correct per evaluated samples | ≥ threshold per eval cycle |
| **Citation Accuracy** | Citations genuinely support the claim they accompany | High; flagged when hallucinated citations occur |
| **Hallucination Rate** | Share of answers containing unsupported claims | Near zero (Section 20) |
| **Agent Routing Accuracy** | Correct specialist chosen for the true intent | High; monitored per intent |
| **Response Time** | End-to-end + TTFT latency | Within budget (Section 31.2) |
| **Token Efficiency** | Tokens per resolved query | Trending down (Section 32.5) |
| **User Satisfaction** | Explicit rating + implicit engagement (resume, copy) | Rising trend |
| **Feedback Score** | Aggregate rating from `feedback` (DATABASE_DESIGN.md §23) | Rising trend |
| **AI Availability** | Successful completions / total attempts | High; fallbacks excluded |
| **Error Rate** | Failures / total runs (timeouts, retries, fallbacks) | Low; monitored per node |

### 38.2 How Metrics Are Captured

| Metric | Source |
| ------ | ------ |
| Retrieval/response/routing | Evaluation harness on sampled conversations + `agent_logs` |
| Latency/tokens/availability | Monitoring pipeline (Section 31) |
| Satisfaction/feedback | `feedback` table aggregation |
| Hallucination/citation | Human + automated review of sampled outputs |

### 38.3 Monitoring & Improvement Loop

```
Capture (logs + feedback)
   ▼
Evaluate (metrics + sampled review)
   ▼
Analyze (root cause: prompt / retrieval / routing / model)
   ▼
Improve (versioned prompt update, retrieval tuning, KB update, model config)
   ▼
Validate (regression run on evaluation harness)
```

| Rule | Detail |
| ---- | ------ |
| Baseline | Metrics baseline captured at launch |
| Cadence | Periodic eval cycles + real-time monitoring dashboards |
| Regression gate | Changes (prompts, retrieval, models, KB) must not regress metrics |
| Feedback-driven | Flagged issues create improvement tickets (Section 29) |
| Reporting | Metrics reported in project reports (FYP deliverables) |

---

## Important

This document is the **permanent AI architecture guide** and the **single source of truth for all AI decisions**.

It must be read together with:

- **PROJECT_RULES.md** — master project rules (agents, RAG, grounding, prompts, workflow order).
- **docs/architecture/ui-ux-design.md** — chat states, response formatting, handoff UX.
- **docs/architecture/BACKEND_ARCHITECTURE.md** — AI integration boundary, layer rules.
- **docs/architecture/DATABASE_DESIGN.md** — persistence, memory, retention, and audit tables.

All AI work — agents, graphs, RAG, memory, prompts, tools, and evaluation — must be derived from this document. Any code that deviates from this design must be corrected before it is accepted.

**This document is architecture and documentation only.** It contains no implementation code. Implementation is derived from these standards, following the project's Development Rules and Definition of Done.

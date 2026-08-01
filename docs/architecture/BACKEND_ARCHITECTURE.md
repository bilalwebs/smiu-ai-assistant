# BACKEND_ARCHITECTURE.md

**Agentic AI-Based University Workflow Automation System**
Multi-Agent Student Support Platform — developed for **Sindh Madressatul Islam University (SMIU)**

> Version: 1.0 · Status: Approved Architecture · Last Updated: July 2026 · Owner: Final Year Project Team
> Scope: Single source of truth for backend services, layers, modules, integrations, and design decisions.
> Sufficiently detailed that the entire backend can be generated without additional architectural instructions.
> This document is **architecture only** — it contains no implementation code, no API endpoints, no database schema, and no prompts.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Backend Philosophy](#2-backend-philosophy)
3. [Technology Stack](#3-technology-stack)
4. [Overall Backend Architecture](#4-overall-backend-architecture)
5. [Project Folder Structure](#5-project-folder-structure)
6. [Layered Architecture](#6-layered-architecture)
7. [Configuration Management](#7-configuration-management)
8. [Dependency Injection](#8-dependency-injection)
9. [Authentication Architecture](#9-authentication-architecture)
10. [Authorization](#10-authorization)
11. [Service Architecture](#11-service-architecture)
12. [Repository Pattern](#12-repository-pattern)
13. [Database Session Management](#13-database-session-management)
14. [Validation Architecture](#14-validation-architecture)
15. [Exception Handling](#15-exception-handling)
16. [Logging Strategy](#16-logging-strategy)
17. [Middleware](#17-middleware)
18. [File Upload Architecture](#18-file-upload-architecture)
19. [Background Tasks](#19-background-tasks)
20. [AI Integration Layer](#20-ai-integration-layer)
21. [RAG Integration Architecture](#21-rag-integration-architecture)
22. [Security Architecture](#22-security-architecture)
23. [Performance Strategy](#23-performance-strategy)
24. [Error Recovery](#24-error-recovery)
25. [Coding Standards](#25-coding-standards)
26. [Testing Strategy](#26-testing-strategy)
27. [Deployment Readiness](#27-deployment-readiness)
28. [Backend Development Rules](#28-backend-development-rules)
29. [Definition of Done](#29-definition-of-done)
30. [Important](#30-important)
31. [Multi-Agent Communication Architecture](#31-multi-agent-communication-architecture)
32. [University Workflow Integration](#32-university-workflow-integration)
33. [AI Development Rules](#33-ai-development-rules)

---

## 1. Introduction

### 1.1 Purpose

This document defines the complete backend architecture for the **Agentic AI-Based University Workflow Automation System**. It specifies the structural boundaries, layer responsibilities, communication rules, integration contracts, and engineering standards that govern every backend module.

It is the **permanent backend reference**. Future backend code — services, repositories, middleware, authentication, AI integration, and RAG pipelines — must be derived from the rules in this document without requiring additional architectural instructions.

### 1.2 Scope

| In scope | Out of scope |
| -------- | ------------ |
| Backend service architecture (FastAPI) | Frontend implementation (see `docs/architecture/ui-ux-design.md`) |
| Layer boundaries and dependency rules | Concrete API endpoint definitions |
| Authentication & authorization design | Database schema / DDL design |
| Service, repository, and session patterns | Prompt engineering or prompt content |
| AI integration and RAG pipeline architecture | Deployment runbooks for external infrastructure |
| Security, logging, validation, and error standards | Non-backend concerns (design, UI, marketing) |
| Testing, deployment readiness, and DoD | — |

### 1.3 Project Overview

The system is a **multi-agent AI support platform** for SMIU students. Students interact with a university chatbot that routes their questions to specialist agents — Coordinator, Admission, Examination, and FAQ (Phase 1) — which answer grounded in an indexed university knowledge base using **Retrieval-Augmented Generation (RAG)**. A FastAPI backend exposes the API, manages authentication, persists conversations, orchestrates the AI layer, and serves the Next.js frontend.

### 1.4 Goals

| # | Goal | Measure of success |
| - | ---- | ------------------ |
| 1 | **Production-ready backend** | Typed, tested, logged, containerized, deployable |
| 2 | **Clean, layered architecture** | Strict dependency direction; no layer-skipping |
| 3 | **Secure by default** | JWT auth, RBAC, input validation, secrets in env only |
| 4 | **Grounded AI answers** | RAG retrieval precedes every LLM response; sources cited |
| 5 | **Extensible agent platform** | New agents added by configuration, not new plumbing |
| 6 | **Research-grade quality** | Architecture itself is an FYP research contribution |
| 7 | **Single source of truth** | Backend generated from this document alone |

### 1.5 Non-Goals

- Not a user-interface specification.
- Not an API reference (endpoints are documented separately as implementation proceeds).
- Not a database design document.
- Not a prompt-engineering document.
- Not a deployment runbook for managed cloud services.
- No multi-tenancy, billing, or external ERP/LMS integration in Phase 1.

---

## 2. Backend Philosophy

| # | Principle | Meaning |
| - | --------- | ------- |
| 1 | **Clean Architecture** | Dependencies point inward; core domain logic never depends on frameworks, HTTP, or the database. |
| 2 | **Modular Design** | Small, independent, well-bounded modules with one responsibility each. |
| 3 | **Separation of Concerns** | Presentation, business logic, data access, and AI concerns never mix in one class or file. |
| 4 | **Scalability** | Async-first, stateless services, poolable connections, horizontally scalable stateless API nodes. |
| 5 | **Maintainability** | Consistent patterns and naming; code that is easy to read, change, and extend. |
| 6 | **Reusability** | Reuse services, repositories, utilities, and prompts before writing anything new. |
| 7 | **Security First** | Secure defaults: validation, JWT, RBAC, least privilege, no secrets in code. |
| 8 | **AI-first Architecture** | The AI layer is a first-class citizen with explicit boundaries, not an afterthought bolted onto routes. |
| 9 | **Production-ready Development** | Every module is typed, tested, logged, and deployable from day one. |
| 10 | **Research-grade Software Design** | The architecture itself demonstrates industry-level engineering discipline as part of the FYP. |

---

## 3. Technology Stack

### 3.1 Selection Summary

| Technology | Version | Role | Why selected |
| ---------- | ------- | ---- | ------------ |
| **FastAPI** | modern (Python 3.12+) | REST API framework | Async-native, automatic OpenAPI docs, first-class Pydantic integration, minimal boilerplate |
| **Python** | 3.12+ | Backend language | Rich AI ecosystem (LangChain/LangGraph), strong typing via PEP 484/604 |
| **SQLAlchemy** | 2.x | ORM | Type-safe ORM with async support, declarative models, session management |
| **Alembic** | latest | Database migrations | Versioned, reproducible schema evolution on top of SQLAlchemy |
| **Pydantic** | v2 | Validation & serialization | Schema validation, settings management, fast (Rust core) |
| **PostgreSQL** | 14+ (production) | Relational database | ACID, JSONB, full-text search, production-grade vector extension path (`pgvector`) |
| **LangGraph** | latest | Agent workflow engine | Graph-based state machines for routing, tool calling, and memory |
| **LangChain** | latest | LLM orchestration | Retrieval chains, embeddings, tool abstractions, model-agnostic interface |
| **Gemini 2.5 Flash** | current | Primary LLM | Fast, cost-efficient, strong grounding; selected as primary model |
| **Grok** | future / optional | Fallback LLM | Provider redundancy behind a model-agnostic abstraction |
| **FAISS** | latest | Vector store | Fast local similarity search over the knowledge base (initial) |
| **JWT** | latest | Authentication | Stateless, standards-based access tokens |
| **Docker** | latest | Containerization | Reproducible builds and environments across dev and prod |
| **Redis** | future | Cache / queue | Session cache, rate limiting, background queues (deferred) |
| **Logging** | stdlib + extras | Observability | Structured, level-based, production-safe logging |
| **Environment Variables** | `.env` | Configuration | Secrets and configuration never live in source code |

### 3.2 Decision Matrix

| Concern | Selected | Alternatives considered | Reason |
| ------- | -------- | ----------------------- | ------ |
| API framework | FastAPI | Django, Flask | Async support, Pydantic-native validation, auto docs, lightweight |
| ORM | SQLAlchemy 2.x | Raw SQL, Tortoise | Type-safe async ORM, Alembic ecosystem, mature |
| Migrations | Alembic | Custom scripts | Versioned, reversible, integrated with SQLAlchemy |
| Validation | Pydantic v2 | Marshmallow, manual | Fast, typed, unified with FastAPI and settings |
| Database | PostgreSQL | MySQL, MongoDB | ACID, JSONB, full-text search, `pgvector` path |
| Vector store | FAISS | ChromaDB, pgvector (prod) | Fast local similarity search; `pgvector` as production-scale path |
| LLM provider | Gemini 2.5 Flash | OpenAI, Grok | Speed + cost + grounding; Grok kept as fallback provider |
| Agent engine | LangGraph | Custom state machine | Built-in state persistence, graph control flow |
| Auth | JWT | Session cookies, OAuth (future) | Stateless, role-friendly, simple for Phase 1 |

**Note (alignment):** This stack reflects the approved decision of the Final Year Project Team — **Gemini 2.5 Flash (primary LLM), Grok (future fallback), FAISS (vector store), PostgreSQL (database)** — and supersedes any earlier draft stack lists.

---

## 4. Overall Backend Architecture

```
Client (Next.js Frontend)
            │
            ▼
   ┌─────────────────┐
   │   FastAPI App    │  middleware: CORS, security headers, request logging, timing
   └─────────────────┘
            │
            ▼
   ┌─────────────────┐
   │   API Layer      │  thin routers → Pydantic in/out → status codes
   └─────────────────┘
            │
            ▼
   ┌─────────────────┐
   │  Service Layer   │  business logic, orchestration, auth, file handling
   └─────────────────┘
            │
            ▼
   ┌─────────────────┐
   │    AI Layer      │  Agent Manager, Coordinator graph, RAG, memory, LLM
   └─────────────────┘
            │
            ▼
   ┌─────────────────┐
   │ Repository Layer │  data access, CRUD, transactions, reusable queries
   └─────────────────┘
            │
   ┌───────┴────────┐
   ▼               ▼
Database         Vector Database
(PostgreSQL)     (FAISS index)
```

### Layer Responsibilities

| Layer | Responsibility |
| ----- | -------------- |
| **Client** | Next.js frontend; talks to the API only via JSON over HTTP(S). |
| **FastAPI App** | Application shell: middleware chain, routing, startup/shutdown lifecycle. |
| **API Layer** | Thin routers that translate HTTP into service calls; validate in/out via Pydantic; never contains business logic. |
| **Service Layer** | Encapsulates business rules, workflows, auth flows, file handling; orchestrates repositories and the AI layer. |
| **AI Layer** | Agent execution, LangGraph workflow, RAG retrieval, memory, LLM generation. Consumed by services, never by routers directly. |
| **Repository Layer** | All data access. Encapsulates ORM queries, CRUD, transactions, and isolation. |
| **Database** | PostgreSQL — relational persistence for students, chats, documents, logs, sessions. |
| **Vector Database** | FAISS index over the knowledge base — similarity retrieval for RAG. |

**Flow rule:** A request enters through the API layer, is validated, delegated to a service, optionally reaches the AI layer, and persists through repositories. The same path applies in reverse for responses.

---

## 5. Project Folder Structure

### 5.1 Backend Service

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/      # Thin HTTP routers (one router per resource)
│   ├── core/                    # App factory, startup/shutdown, lifespan, wiring
│   ├── config/                  # Pydantic Settings, environment loading
│   ├── dependencies/            # FastAPI dependency providers (auth, db, services)
│   ├── middleware/              # CORS, security headers, request logging, timing
│   ├── security/                # Password hashing, JWT encode/decode, token types
│   ├── services/                # Business logic — one service per feature
│   ├── repositories/            # Data access — one repository per aggregate
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response contracts
│   ├── database/                # Engine, async session factory, Base, health helpers
│   ├── exceptions/              # Domain and infrastructure exception types
│   ├── logging/                 # Logging configuration and formatters
│   ├── utils/                   # Pure, reusable helper functions
│   └── main.py                  # FastAPI application entrypoint
├── alembic/
│   ├── versions/                # Generated migration revisions
│   └── env.py                   # Migration environment wiring
├── tests/
│   ├── unit/                    # Isolated unit tests
│   ├── integration/             # Service + DB + AI integration tests
│   ├── repositories/            # Repository tests against a real/test DB
│   ├── services/                # Service-layer behavior tests
│   └── ai/                      # Agent, routing, retrieval, RAG tests
├── scripts/                     # Dev automation: lint, format, type-check, seed
├── docs/                        # Backend-specific documentation
├── Dockerfile
├── requirements.txt             # Runtime dependencies (pinned)
├── requirements-dev.txt         # Dev/test dependencies
└── .env.example                 # Environment variable template
```

### 5.2 AI Layer (per PROJECT_RULES.md — lives in the `ai/` service)

```
ai/
├── agents/            # Agent definitions: Coordinator, Admission, Examination, FAQ
├── graphs/            # LangGraph state machines (workflow engine)
├── rag/               # Chunking, embedding strategy, retriever, context builder
├── prompts/           # Prompt templates — owned per agent (no prompts in routes)
├── memory/            # Conversation memory and state persistence
├── tools/             # Agent tools (retrieval, formatting; future university APIs)
└── utils/             # AI-layer shared helpers
```

### 5.3 Knowledge Base (project root, per PROJECT_RULES.md)

```
knowledge/
├── admission/         # Admission guides, eligibility, required documents
├── examination/       # Date sheets, results, exam rules
├── faq/               # General university FAQs
├── documents/         # Policies and official documents
└── vectorstore/       # FAISS index files (generated)
```

### 5.4 Folder Ownership Rules

- Every folder has **one responsibility** — never mix concerns inside a folder.
- New code must land in the **existing correct folder**; never create parallel or duplicate structures.
- The **backend service owns** API, business logic, and data access. The **AI service owns** agents, graphs, RAG, memory, prompts, and tools. The **knowledge root** owns source documents and the vector index.

---

## 6. Layered Architecture

### 6.1 Layers

| Layer | Owns | Depends on |
| ----- | ---- | ---------- |
| **Presentation** | API routers, schemas, HTTP concerns | Service layer only |
| **Business** | Services, domain rules, workflows | Repositories, AI layer, infrastructure |
| **AI** | Agents, graphs, RAG, memory, LLM calls | Repositories (read), vector store, LLM provider |
| **Repository** | Data access, queries, transactions | Persistence layer |
| **Persistence** | SQLAlchemy engine, sessions, migrations, models | Database |
| **Infrastructure** | Config, logging, middleware, external clients | External systems |

### 6.2 Communication Rules

- **Presentation → Business:** routers call services; never the reverse.
- **Business → Repository:** services call repository interfaces; never raw ORM sessions.
- **Business → AI:** services invoke the AI layer through an explicit integration boundary.
- **Repository → Persistence:** repositories use the session and ORM only.
- **AI → Repository (read):** the AI layer may read knowledge/document metadata through repositories; it never writes application data directly.
- **No cross-layer shortcuts:** a router must never touch the database, the AI layer must never be reached from a router, and business logic must never appear in a repository.

### 6.3 Dependency Direction

```
Presentation  ──►  Business  ──►  Repository  ──►  Persistence
                     │  │
                     │  └──►  AI Layer  ──►  Vector Store / LLM
                     ▼
              Infrastructure (config, logging, security)
```

- Dependencies always point **downward** (concrete) or **inward** (via interfaces).
- The **Business layer** is the composition root owner: it decides which repositories and AI services are used.
- Dependency injection (Section 8) enforces this direction; nothing is instantiated by hand inside a router.

---

## 7. Configuration Management

### 7.1 Environment Variables

All configuration and secrets are loaded from a local `.env` file (gitignored); `.env.example` holds the committed template. Core variables (from PROJECT_RULES.md) plus backend-extended settings:

| Variable | Purpose | Scope |
| -------- | ------- | ----- |
| `GEMINI_API_KEY` | LLM API key for Gemini 2.5 Flash | Secret |
| `DATABASE_URL` | Database connection string (SQLite dev / PostgreSQL prod) | Config |
| `JWT_SECRET` | Secret for signing and verifying JWT tokens | Secret |
| `FAISS_PATH` | File path to the FAISS vector index | Config |
| `SECRET_KEY` | App-level secret for encryption and signing | Secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | Config |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | Config |
| `ENVIRONMENT` | `development` / `testing` / `production` | Config |
| `CORS_ORIGINS` | Allowed frontend origins | Config |
| `REDIS_URL` | Future cache/queue connection | Secret (future) |
| `LOG_LEVEL` | Runtime logging threshold | Config |

### 7.2 Settings Pattern

- Settings are modeled as a single **Pydantic Settings** class (validation + typing at startup).
- Settings are loaded **once** at application startup and exposed through dependency injection.
- Environment variables override `.env` values; explicit OS environment wins in production.
- Unknown or malformed settings fail fast at startup — never at request time.

### 7.3 Secrets & API Keys

- Never hardcode secrets or API keys in source code.
- Never commit `.env` files; commit only `.env.example`.
- Never log secrets, API keys, or tokens (Section 16).
- Rotate keys through configuration only — no code changes.
- Least privilege: each service holds only the keys it needs.

### 7.4 Configuration Rules

- Configuration is code-free: no hardcoded branches in application logic — read from settings.
- `ENVIRONMENT` gates behaviour (logging, docs exposure, CORS) — never via ad-hoc checks scattered in code.

### 7.5 Development vs Production

| Concern | Development | Production |
| ------- | ----------- | ---------- |
| Database | SQLite or local PostgreSQL | PostgreSQL (managed) |
| Docs (`/docs`) | Enabled | Disabled or auth-gated |
| Log level | `DEBUG` | `INFO`+ |
| CORS | Local origins | Explicit production origins |
| Secrets | Local `.env` | Environment / secret manager |
| LLM | Same model (2.5 Flash) | Same model; quota/rate protection |

---

## 8. Dependency Injection

### 8.1 Strategy

FastAPI's native dependency injection is the **only** mechanism for wiring services, sessions, and security into routers. Everything a handler needs arrives as a typed dependency parameter.

| Component | Provider | Consumed by |
| --------- | -------- | ----------- |
| Database session | `database` dependency (request-scoped) | Repositories via services |
| Current user | `security` dependency (JWT → user) | Protected routers |
| Services | `dependencies` factories (per request or singleton) | Routers |
| AI layer entry | `dependencies` factory (shared) | Services |
| Settings | singleton provider | Everything at startup |

### 8.2 Shared Services

- Services with **no per-request state** are created once (singleton) and reused.
- Services holding **request-scoped state** (e.g., a session-bound unit of work) are created per request.
- No service is ever instantiated inside a router; routers receive ready instances.

### 8.3 Database Session Lifecycle

- The session dependency opens a session at the start of the request and **closes it when the request ends**.
- Commits are explicit and performed by the calling service/repository — never implicitly by the framework.
- On unhandled error, the session rolls back before being released back to the pool.
- The same session is shared by all repositories used within one request (unit-of-work).

### 8.4 Authentication Dependencies

- `get_current_user` — decodes the JWT, loads the user, raises 401 on failure.
- `require_role(...)` — wraps `get_current_user` and enforces role membership (Section 10).
- These dependencies protect routes declaratively; routers never parse tokens themselves.

### 8.5 AI Dependencies

- The AI layer is injected as a boundary object (e.g., an agent-service facade) with a stable interface.
- Routers depend on the facade via services only; swapping the LLM provider or adding agents requires no route changes.

---

## 9. Authentication Architecture

### 9.1 Token Model

| Token | Purpose | Lifetime | Storage |
| ----- | ------- | -------- | ------- |
| **Access token** | Authorizes API requests | Short (e.g., minutes) | Client memory (never localStorage if avoidable) |
| **Refresh token** | Obtains new access tokens | Longer (e.g., days) | Server-side session record + client secure storage |

### 9.2 Password Hashing

- Passwords are hashed with a **strong, slow, salted** algorithm (bcrypt/argon2 family).
- Plaintext passwords never appear in logs, responses, or memory any longer than required.
- Re-hash/upgrade logic supports algorithm rotation without user disruption.

### 9.3 Flows

| Flow | Steps |
| ---- | ----- |
| **Registration** | Validate input → hash password → create account (unverified) → send verification → respond. |
| **Email verification** | Signed verification link → validate token → mark verified → notify success. |
| **Login** | Validate credentials → issue access + refresh tokens → record session → respond. |
| **Refresh** | Present valid refresh token → validate session → rotate/issue new access token. |
| **Logout** | Revoke refresh token/session → invalidate client tokens. |
| **Password reset** | Request reset → signed reset link → set new password → revoke existing sessions. |

### 9.4 Session Management

- Sessions are persisted server-side (e.g., `sessions` table) and linked to a user.
- Logout and password change revoke active sessions.
- Expired or revoked refresh tokens fail cleanly with a specific error code that the client maps to "sign in again".

### 9.5 Roles

| Role | Phase | Description |
| ---- | ----- | ----------- |
| **Student** | Phase 1 | Self-service: requests, chat, profile, notifications |
| **Admin** | Future | Manage students, requests, knowledge base, agents, analytics |
| **Faculty** | Future | Read-only / department-scoped support (planned only) |

---

## 10. Authorization

### 10.1 Role-Based Access Control

- Every authenticated request carries the user's **role** (derived from the verified identity, never from client input).
- Route access is declared via role-checking dependencies on the router (Section 8.4).
- Frontend navigation visibility is informational only — **enforcement always happens server-side**.

### 10.2 Permission Model

| Concern | Rule |
| ------- | ---- |
| Resource ownership | Users access only their own resources unless a role permits otherwise |
| Role checks | `require_role` dependencies at route level |
| Data scoping | Repositories scope queries by the current user's context |
| Default | Deny by default; access is granted explicitly |

### 10.3 Protected Routes

- All routes except public auth endpoints are protected by `get_current_user`.
- Admin routes additionally require the admin role.
- Authorization failures return 401 (unauthenticated) or 403 (forbidden) with consistent error shapes.

### 10.4 Future Expansion

- Permission granularity can evolve from role-level to permission-level checks without changing route structure.
- Faculty access is planned as a scoped role (department-limited) — no architectural change required.

---

## 11. Service Architecture

### 11.1 Communication Model

```
Router ──► Service ──► Repository ──► Database
              │
              └──► AI Layer (integration boundary)
```

### 11.2 Rules

| Rule | Detail |
| ---- | ------ |
| **Services never access the database directly** | All persistence goes through repositories. |
| **Services use repositories** | Services depend on repository interfaces, not ORM sessions. |
| **Repositories never contain business logic** | Repositories translate data access only; no rules, no flows. |
| **Controllers remain thin** | Routers validate, call one service, and return; no business logic in routes. |
| **One service per feature** | E.g., auth service, request service, chat service, user service. |
| **No duplicate business logic** | Shared logic is extracted into a shared service or helper — never copied. |

### 11.3 Orchestration

- Services coordinate: validate → authenticate → call repository/AI → build result → emit logs/events.
- A service may compose multiple repositories (unit of work) and multiple AI calls.
- Services return typed results (schemas/domain objects); they raise typed exceptions on failure (Section 15).

---

## 12. Repository Pattern

### 12.1 Responsibilities

| Repository duty | Detail |
| --------------- | ------ |
| **CRUD** | Standard create, read, update, delete operations for an aggregate |
| **Transactions** | Begins and commits transaction boundaries owned by the caller (service) |
| **Reusable queries** | Named, typed query methods (e.g., `find_by_email`, `paginate_active`) |
| **Isolation** | Works inside the request-scoped session (unit of work) |

### 12.2 Rules

- One repository per aggregate/domain entity (e.g., user, request, conversation, session).
- Repositories expose **intent-named methods**, not raw query builders exposed to callers.
- Repositories never implement business rules, validation, or flows.
- Return types are typed (models or Pydantic projections); no untyped result sets.

### 12.3 Transactions

- Transaction boundaries live at the **service level**, not inside repositories.
- A service opens a unit of work, performs multiple repository calls, and commits once.
- On any failure the unit of work rolls back atomically.

---

## 13. Database Session Management

| Concern | Strategy |
| ------- | -------- |
| **Session lifecycle** | Request-scoped session via dependency injection; created on request start, closed on end. |
| **Commit** | Explicit commits performed by the calling service after its work succeeds. |
| **Rollback** | Automatic rollback on any unhandled exception before the session is released. |
| **Transactions** | Unit-of-work per request; commit-once at the end of successful orchestration. |
| **Connection pool** | Sized pool (SQLAlchemy + async driver); tuned for expected concurrency. |
| **Best practice** | Never share sessions between requests; never use sessions after close; never write to the DB from routers or the AI layer directly. |

---

## 14. Validation Architecture

### 14.1 Pydantic v2 Contracts

| Layer | What is validated | Mechanism |
| ----- | ----------------- | --------- |
| **Input** | Request bodies, query params, path params | Pydantic request schemas on every router |
| **Output** | Response bodies | Pydantic response schemas on every router |
| **Business** | Domain rules and state transitions | Service-layer checks before persistence |
| **Settings** | Configuration at startup | Pydantic Settings |

### 14.2 Rules

- **Validate everything at the boundary** — never trust client input.
- Response schemas guarantee a stable, documented API contract regardless of internal state.
- Business validation lives in services; schema validation lives in schemas — they are not interchangeable.
- Validation failures produce consistent 422 responses with structured detail (Section 15).

---

## 15. Exception Handling

### 15.1 Global Exception Handler

A single, application-wide handler translates every exception into a consistent error response. Routers and services never catch-and-format ad hoc.

### 15.2 Error Categories

| Category | HTTP status | Notes |
| -------- | ----------- | ----- |
| **Validation errors** | 422 | Field-level detail from Pydantic |
| **Authentication errors** | 401 | Missing/invalid/expired credentials |
| **Authorization errors** | 403 | Authenticated but not permitted |
| **Not found** | 404 | Resource does not exist |
| **AI errors** | 502 / 503 | LLM, retrieval, or agent failures (mapped to friendly messages) |
| **Database errors** | 500 (or 409 on conflicts) | Mapped, logged, never leaked |
| **Unknown errors** | 500 | Logged in full; client sees a generic message |

### 15.3 Consistent Error Shape

Every error response follows the same envelope (error code, message, details). Error codes are stable identifiers the frontend can branch on. **Stack traces are never exposed to the client** — full details remain in server logs.

---

## 16. Logging Strategy

### 16.1 Levels

| Level | Use |
| ----- | --- |
| `DEBUG` | Development detail — never in production by default |
| `INFO` | Successful operations, key lifecycle events |
| `WARNING` | Recoverable anomalies, retries, degraded behavior |
| `ERROR` | Failures that need attention |
| `CRITICAL` | System-level failures |

### 16.2 What is Logged

| Category | Events |
| -------- | ------ |
| **Request logging** | Method, path, status, duration, user ID (when available) |
| **AI logging** | Routing decision, selected agent, retrieval run, LLM response time |
| **Database logging** | Slow queries, transaction failures (no SQL dumps of sensitive data) |
| **Error logging** | Full exception details with correlation IDs |
| **Security logging** | Login failures, token rejections, authorization denials, suspicious activity |

### 16.3 Production Rules

- **Never log secrets, API keys, passwords, or tokens** (PROJECT_RULES.md).
- Structured, machine-parseable logs (JSON) with timestamps and correlation IDs.
- Log level configured via environment; production defaults to `INFO`.
- Sensitive fields are redacted before logging.

---

## 17. Middleware

| Middleware | Responsibility | Status |
| ---------- | -------------- | ------ |
| **Authentication middleware** | Rejects requests without valid tokens before routing (fast-fail) | Phase 1 |
| **Request logging** | Logs every request with status and duration | Phase 1 |
| **CORS** | Allows configured frontend origins only | Phase 1 |
| **Security headers** | Sets secure response headers (CSP, X-Frame-Options, etc.) | Phase 1 |
| **Rate limiting** | Protects public and AI endpoints from abuse | Future (Redis-backed) |
| **Performance monitoring** | Captures timing and health telemetry | Phase 1 (basic) |
| **Request timing** | Measures per-request latency for logs and monitoring | Phase 1 |

Ordering note: security headers and CORS run outermost; authentication fast-fails before handlers; logging wraps everything for accurate timing.

---

## 18. File Upload Architecture

| Concern | Design |
| ------- | ------ |
| **Supported uploads** | Documents/attachments tied to requests and knowledge ingestion (Phase 1: common text/document formats) |
| **Validation** | Type (MIME) whitelist, size limits, content checks — enforced at the API boundary |
| **Storage strategy** | Local filesystem in a dedicated storage path during Phase 1; metadata tracked in the database |
| **Security** | Random-safe filenames, no direct execution of uploaded content, virus-scan notice, never served from a code path |
| **Future cloud storage** | Storage behind a repository/service interface so cloud (e.g., blob storage) can replace local storage without changing business logic |

---

## 19. Background Tasks

| Task | Phase | Notes |
| ---- | ----- | ----- |
| **Email delivery** | Phase 1 | Verification, reset, notifications — async, non-blocking |
| **Notifications** | Phase 1 | Created and dispatched without blocking the request |
| **Embedding generation** | Phase 1 | Document chunks embedded asynchronously during ingestion |
| **Knowledge indexing** | Phase 1 | Chunking → embedding → FAISS upsert as a background job |
| **Future queue support** | Future | Redis-backed task queue for durable, retryable jobs |

Rule: long-running or failure-prone work (email, embeddings, indexing) is never executed inline in a request handler.

---

## 20. AI Integration Layer

The AI layer is a distinct boundary consumed by services through a stable facade. It contains **no prompt engineering** here — prompts are versioned assets owned per agent in the AI service (PROJECT_RULES.md).

### 20.1 Components

| Component | Responsibility |
| --------- | -------------- |
| **AI Services** | Facade exposing chat/handoff/retrieval operations to the business layer |
| **Agent Manager** | Registry and lifecycle of agents; routes to the correct specialist |
| **Coordinator Agent** | Entry node: intent detection and routing to specialist agents |
| **LangGraph Integration** | State-machine workflow: detect → select → retrieve → generate → persist |
| **Tool Calling Layer** | Agents invoke tools (retrieval, formatting; future university APIs) with typed results |
| **Memory Layer** | Conversation history and agent state persisted for continuity |
| **RAG Layer** | Retrieval over the knowledge base; context construction (Section 21) |
| **LLM Layer** | Model-agnostic generation (Gemini primary, Grok fallback) with structured outputs |
| **Response Builder** | Assembles the final answer, sources/citations, and handoff metadata |

### 20.2 Boundary Rules

- Routers never call the AI layer; only services do.
- The AI layer never writes application data directly — it persists via the same repositories when needed.
- The LLM provider is behind an abstraction; switching primary/fallback requires configuration, not route or service changes.
- AI failures surface as typed errors mapped to friendly responses (Sections 15 and 24).

### 20.3 Phase 1 Agents

| Agent | Responsibility |
| ----- | -------------- |
| **Coordinator Agent** | Detect intent · route to the correct specialist · manage the workflow · aggregate responses |
| **Admission Agent** | Admission requirements · eligibility · required documents · merit queries · admission process |
| **Examination Agent** | Date sheet · results · admit cards · examination rules · improvement policy |
| **FAQ Agent** | General university FAQs · departments · office timings · campus information · contact information |

Future agents (Finance, Registration, Library, Hostel, IT Support, Scholarship) are placeholders added to the Agent Manager registry without new plumbing.

---

## 21. RAG Integration Architecture

### 21.1 Pipeline

```
Knowledge documents (knowledge/)
        │  ingestion
        ▼
   Chunking ──► Embedding ──► FAISS vector store
        │                         ▲
        │                         │  retrieval
        ▼                         │
   Student question ──► Retriever ─┘
                            │
                            ▼
                    Context Builder
                            │
                            ▼
                    LLM generation (grounded)
                            │
                            ▼
                    Response + citations
```

### 21.2 Components

| Component | Responsibility |
| --------- | -------------- |
| **Knowledge documents** | Source files organized by category in `knowledge/` (admission, examination, faq, documents). |
| **Chunking** | Documents split into retrievable chunks with metadata (source, category). |
| **Embedding** | Chunks embedded via the configured embedding provider; vectors stored per chunk. |
| **Vector store** | FAISS index at `knowledge/vectorstore/`; regenerable from source documents. |
| **Retriever** | Similarity search over the index returning the top-relevant chunks for a query. |
| **Context builder** | Assembles retrieved chunks into a grounded context for the LLM; deduplicates and prioritizes. |
| **Citation flow** | Sources are tracked through the pipeline and surfaced with answers (collapsible, per UI spec). |
| **Response pipeline** | Retrieve → build context → generate → attach citations → return through the AI facade. |

### 21.3 Grounding Rules (from PROJECT_RULES.md)

- **Never hallucinate** — answers must always be grounded in retrieved knowledge.
- **Always retrieve before answering** — RAG precedes LLM generation.
- If information is unavailable, say so clearly and recommend the correct university department.

---

## 22. Security Architecture

| Control | Design |
| ------- | ------ |
| **Password hashing** | Strong salted hashing (bcrypt/argon2 family); never plaintext |
| **JWT** | Signed access/refresh tokens; short-lived access; server-side sessions |
| **Secrets** | Environment variables only; never committed; never logged |
| **Input validation** | Pydantic v2 at every boundary |
| **SQL injection prevention** | Parameterized ORM queries only — never string-built SQL |
| **XSS prevention** | Output escaped/sanitized; no unsafe HTML from user content |
| **CORS** | Explicit allow-list of frontend origins |
| **Security headers** | CSP, frame/cache protections set by middleware |
| **Role-based security** | Server-enforced RBAC (Section 10) |
| **Least privilege** | Default-deny; each component holds only the access it needs |
| **Audit trail** | Security events logged (login failures, denials, token rejections) |

---

## 23. Performance Strategy

| Technique | Application | Status |
| --------- | ----------- | ------ |
| **Async programming** | FastAPI async handlers; non-blocking I/O throughout | Phase 1 |
| **Connection pooling** | Sized async DB pool; avoid per-request connect overhead | Phase 1 |
| **Caching strategy** | Cache frequent retrievals/static data | Future (Redis) |
| **Lazy loading** | Defer heavy imports and AI initialization until needed | Phase 1 |
| **Background processing** | Emails, embeddings, indexing off the request path | Phase 1 |
| **Scalability** | Stateless API nodes → horizontal scale behind a load balancer | Future |

Design intent: the API is **stateless**, so any number of instances can serve traffic; sessions and state live in the database (and later Redis).

---

## 24. Error Recovery

| Concern | Strategy |
| ------- | -------- |
| **Retry strategy** | Transient failures (network, rate limits) retried with bounded backoff; idempotent operations only |
| **Graceful failure** | Services degrade stepwise — a retrieval failure does not take down chat; a fallback answer is produced |
| **AI failure recovery** | LLM/agent failures map to typed errors → friendly message + retry option (UI contracts in the UX spec) |
| **Database recovery** | Connection errors retried safely; transactions rolled back atomically |
| **Timeout handling** | AI calls bounded by timeouts; slow responses produce a clear "taking too long" state |
| **Fallback responses** | Grounded answer unavailable → explicit "information not available" + department recommendation |

---

## 25. Coding Standards

| Standard | Rule |
| -------- | ---- |
| **Strict type hints** | Every function and method fully typed (params + return) |
| **Docstrings** | Modules, classes, and public functions documented (Google/NumPy style) |
| **Naming conventions** | Python files/functions/variables `snake_case`; classes `PascalCase`; constants `UPPER_CASE`; tables `snake_case`; endpoints `kebab-case` (PROJECT_RULES.md) |
| **One responsibility per file** | A file has a single clear purpose |
| **One service per feature** | Feature logic is owned by its service — no sprawl |
| **No circular dependencies** | Layer direction enforced; imports point downward only |
| **No business logic in controllers** | Routers only translate HTTP ↔ service calls |
| **No database logic in controllers** | Routers never touch ORM, sessions, or queries |

---

## 26. Testing Strategy

| Test level | Scope | Example targets |
| ---------- | ----- | --------------- |
| **Unit** | Isolated logic, mocked boundaries | Services, helpers, validation rules |
| **Integration** | Real interactions between layers | Service + repository + database |
| **Repository** | Query behavior against a real/test DB | CRUD, scoping, transactions |
| **Service** | Business workflows end-to-end at service level | Auth flows, request lifecycle |
| **AI** | Agents, routing, retrieval, RAG quality | Coordinator routing, grounding, citations |
| **Load (future)** | Behavior under concurrency | API throughput, pool behavior |

Rules: tests are part of the feature (Definition of Done); tests never hit the real production database; external LLM calls are mocked or gated in CI.

---

## 27. Deployment Readiness

| Concern | Design |
| ------- | ------ |
| **Docker** | Multi-stage Dockerfile; slim production image; non-root runtime |
| **Environment separation** | `development` / `testing` / `production` via `ENVIRONMENT`; isolated settings |
| **Health checks** | `/health` endpoint — liveness and readiness probes for orchestration |
| **Production config** | Secrets from environment/secret manager; docs gated; log level `INFO` |
| **Logging** | Structured, correlation-tagged, JSON output for production aggregators |
| **Monitoring** | Request timing, error rates, AI latency/fallback metrics exposed |
| **Scalability** | Stateless nodes; migrations run as a separate step; future Redis for cache/queues |

---

## 28. Backend Development Rules

Every backend implementation **must**:

- Follow **PROJECT_RULES.md**.
- Follow **BACKEND_ARCHITECTURE.md** (this document).
- Use **FastAPI best practices**.
- Use **SQLAlchemy 2.x**.
- Use **Alembic** for migrations.
- Use **Pydantic v2** for validation.
- Use **strict typing**.
- Follow **Clean Architecture**.
- Use the **Repository Pattern**.
- Use **Dependency Injection**.
- Be **production-ready**.
- Be **secure by default**.
- **Never duplicate business logic**.
- **Never place business logic inside API routes**.
- **Never bypass repositories**.

---

## 29. Definition of Done

A backend feature is complete only when it is:

- **Fully typed** — no implicit or missing types.
- **Fully validated** — Pydantic contracts on all boundaries.
- **Tested** — unit/integration coverage per Section 26.
- **Logged** — relevant events captured per Section 16.
- **Error handled** — typed exceptions and consistent error responses.
- **Secure** — auth/RBAC, validation, no secrets, no injections.
- **Documented** — OpenAPI and `docs/` updated.
- **Reusable** — no duplicated logic; shared parts extracted.
- **Modular** — one responsibility per module.
- **Production ready** — typed, tested, logged, and deployable.

---

## 30. Important

This document is the **permanent backend architecture guide**.

It is the **single source of truth for backend development**. All future backend code — services, repositories, middleware, authentication, AI integration, and RAG pipelines — must strictly follow this architecture.

This document is **architecture only**. It contains no implementation code, no API endpoints, no database schema, and no prompts. All implementation must be derived from these standards and the design decisions above.

The backend follows the project's master rules in **PROJECT_RULES.md** and integrates with the frontend defined in **`docs/architecture/ui-ux-design.md`**.

---

## 31. Multi-Agent Communication Architecture

The multi-agent system is orchestrated as a **single LangGraph workflow** with one entry point (the Coordinator Agent) and a set of specialist agents. Agents do not talk to each other directly — all communication flows through the shared graph state and the Coordinator.

```
Student question
        │
        ▼
Coordinator Agent (entry node)
        │
        ├── intent detection
        │
        ▼
   Specialist Agent
  ┌─────────┬──────────┬──────────┐
  │Admission│Examination│  FAQ     │  (Phase 1)
  └─────────┴──────────┴──────────┘
        │
        ├── RAG retrieval ──► FAISS
        │
        ▼
Response aggregation ──► memory update ──► return to caller
```

### 31.1 Coordinator Agent Responsibilities

| Responsibility | Detail |
| -------------- | ------ |
| **Intent detection** | Classifies the incoming question (admission, examination, FAQ, general). |
| **Routing** | Selects the correct specialist agent based on the detected intent. |
| **Workflow management** | Owns the graph lifecycle: start, route, retrieve, aggregate, persist. |
| **Handoff execution** | Transfers the conversation to the specialist and signals the handoff to the UI. |
| **Response aggregation** | Combines specialist output, citations, and status into one typed response. |
| **Fallback routing** | Handles ambiguous or out-of-scope intents with a clear, grounded response. |

The Coordinator is the **only** agent that can be entered externally; specialists are reached only through the Coordinator.

### 31.2 Specialist Agent Communication

- Specialist agents are **stateless workers**: they receive a task via graph state, execute against their own knowledge domain, and write results back to state.
- They never accept direct external calls; the Coordinator is the sole gateway.
- Each specialist owns its prompt, its retrieval scope, and its tool set — modules remain isolated and swappable.

| Agent | Communication role |
| ----- | ------------------ |
| **Admission Agent** | Receives admission intents; retrieves admission knowledge; returns grounded answer + sources. |
| **Examination Agent** | Receives examination intents; retrieves exam knowledge; returns grounded answer + sources. |
| **FAQ Agent** | Receives general FAQ intents; retrieves FAQ knowledge; returns grounded answer + sources. |

### 31.3 Message Passing

- Messages are **typed state transitions** within the LangGraph workflow, not free-form calls between agents.
- Each step receives the current graph state and returns an updated state.
- Conversation turns are appended to shared state and persisted to the conversation store at the end of the run.

| Message type | Contents |
| ------------ | -------- |
| **User turn** | Query text, user context, conversation ID |
| **Routing signal** | Detected intent, selected agent, confidence |
| **Agent result** | Generated answer, retrieved sources, status |
| **Aggregated response** | Final answer, citations, handoff metadata, completion status |

### 31.4 Agent Handoff

- A handoff occurs when the Coordinator routes to a specialist — it is **always explicit and visible**.
- The handoff is represented in the response metadata and surfaced in the UI as a divider chip (e.g., "Routed to Examination Agent →") per the UX specification.
- Handoffs never lose the conversation context; the full state carries through the transition.

### 31.5 Shared State

| State item | Owner | Purpose |
| ---------- | ----- | ------- |
| Conversation context | Coordinator | Carries user turns and history through the workflow |
| Routing decision | Coordinator | Records intent and selected specialist |
| Retrieved context | RAG layer | Grounds the specialist's answer with sources |
| Agent output | Specialist | Answer content and citations for aggregation |
| Memory snapshot | Memory layer | Persisted history for continuity across sessions |

Shared state is the **single source of truth during a run**; it is written to persistent storage only at defined checkpoints.

### 31.6 Response Aggregation

- The Coordinator collects the specialist's answer, retrieved citations, and status into a **single typed response envelope**.
- Citations accompany any answer grounded in RAG data (collapsible in the UI).
- Aggregation normalizes output regardless of which specialist produced it — the caller never branches on agent identity.

### 31.7 Failure Handling

| Failure | Handling |
| ------- | -------- |
| Intent undetectable | Coordinator returns a clarifying response; no specialist is invoked. |
| Retrieval failure | Degrade to a best-effort grounded response or a clear "information unavailable" message. |
| Specialist error | Coordinator catches, logs, and returns a friendly error with retry signal — the workflow is never left half-executed. |
| LLM timeout / rate limit | Typed AI error mapped to a friendly message; bounded retries (Section 24). |
| Memory persistence failure | Run completes and returns to the caller; persistence retried via background handling. |

### 31.8 Future Agent Scalability

- New specialists are added to the **Agent Manager registry** and the routing table — no new plumbing, no changes to callers.
- Future agents (Finance, Registration, Library, Hostel, IT Support, Scholarship) reuse the same message, state, and aggregation contracts.
- Routing can later be enriched (multi-intent, confidence thresholds) without changing the communication architecture.

---

## 32. University Workflow Integration

Workflows connect the AI layer, the request lifecycle, and university departments. This section describes the **architecture** of each workflow — not their implementation.

### 32.1 Student Requests

- A request is the core **persistable unit** of student activity: created from the portal or converted from an AI conversation.
- The request lifecycle follows the standardized status model (Draft → Submitted → In Review → Assigned → Processing → Resolved → Closed / Rejected) defined in the UX specification.
- Every request carries: type, department target, priority, timeline, status badge, and responsible department (when available).

### 32.2 Admission Workflow

| Stage | Architecture |
| ----- | ------------ |
| Question / intent | Admission Agent retrieves admission knowledge (requirements, eligibility, documents, merit). |
| Grounded answer | RAG-grounded response with citations; next-step guidance. |
| Escalation | If action is needed, the workflow converts the conversation into a request routed to the admission department. |
| Tracking | Request becomes trackable in the student's dashboard with status and timeline. |

### 32.3 Examination Workflow

| Stage | Architecture |
| ----- | ------------ |
| Question / intent | Examination Agent retrieves exam knowledge (date sheets, results, admit cards, rules, improvement policy). |
| Grounded answer | RAG-grounded response with citations. |
| Escalation | Confirmation or correction needs convert to a request routed to the examination department. |
| Tracking | Status, timeline, and department ownership tracked end-to-end. |

### 32.4 FAQ Workflow

| Stage | Architecture |
| ----- | ------------ |
| Question / intent | FAQ Agent retrieves general knowledge (departments, office timings, campus info, contact). |
| Grounded answer | RAG-grounded response with citations. |
| Self-service | Most FAQ intents resolve without creating a request — escalation is the exception, not the default. |

### 32.5 Notification Flow

```
Workflow event (request status change, AI response, deadline)
        │
        ▼
   Notification service
        │
        ├── create notification record
        ├── determine priority (Critical / High / Medium / Low)
        ├── dispatch (in-app feed; email as async background task)
        │
        ▼
   Student UI (bell feed, toasts)
```

- Notifications are generated by **workflow events**, never ad hoc.
- Priority (per the UX specification) drives badge color, ordering, toast appearance, and grouping.
- Dispatch is non-blocking — created and delivered as background tasks (Section 19).

### 32.6 Request Tracking

- Every request exposes a **timeline** of status transitions with timestamps and the responsible department.
- Tracking reads flow through repositories; status changes are transactional and logged.
- Students see current status, history, and department ownership; the AI layer may query request status to answer "where is my request?" type questions.

### 32.7 Department Routing

- Requests carry a **department target**; the routing decision is data-driven (configuration), not hardcoded in services.
- Routing aligns with Phase 1 scope: Admission, Examination, and general support. Each department is represented by an agent and a routing entry.

### 32.8 Future Department Expansion

- New departments join by adding a **routing entry + agent registry entry + department configuration** — no change to the workflow or request engine.
- Workflow contracts (request, notification, tracking, escalation) are department-agnostic by design.
- This keeps the platform extensible across the university without re-architecting the backend.

---

## 33. AI Development Rules

Every AI implementation **must**:

- Follow the **AI Architecture** (agents, graphs, RAG, memory, tools — PROJECT_RULES.md).
- Follow the **Backend Architecture** (BACKEND_ARCHITECTURE.md, this document).
- **Never bypass the Coordinator Agent** — all external input enters the workflow through the Coordinator.
- **Always use the LangGraph workflow** — no ad-hoc agent orchestration outside the graph.
- **Always use RAG before LLM generation when knowledge is required** — grounding precedes generation.
- **Never expose prompts to users** — prompts are internal assets, never returned to the client.
- **Never hallucinate unavailable university information** — say "information unavailable" and recommend the correct department.
- **Always provide citations when RAG data is used.**
- **Keep AI services modular** — one responsibility per module.
- **Separate prompts, tools, memory, and graph logic** — no mixing concerns inside an agent file.

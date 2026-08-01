# IMPLEMENTATION_PLAN.md

**Agentic AI-Based University Workflow Automation System**
Multi-Agent Student Support Platform — developed for **Sindh Madressatul Islam University (SMIU)**

> Version: 1.0 · Status: Approved Architecture · Last Updated: August 2026 · Owner: Final Year Project Team
> Scope: Single source of truth for the complete implementation sequence — project initialization to production deployment. Defines phases, tasks, dependencies, milestones, schedule, quality gates, and deliverables.
> Sufficiently detailed that a new developer can implement the project step by step without additional planning.
> This document is **planning and documentation only** — it contains no implementation code, no Python, no SQL, no Docker configuration, and no scripts.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Development Principles](#2-development-principles)
3. [Project Phases](#3-project-phases)
4. [Detailed Implementation Tasks](#4-detailed-implementation-tasks)
5. [Feature Dependency Matrix](#5-feature-dependency-matrix)
6. [Milestones](#6-milestones)
7. [Weekly Development Roadmap](#7-weekly-development-roadmap)
8. [Development Checklist](#8-development-checklist)
9. [Risk Management](#9-risk-management)
10. [Quality Gates](#10-quality-gates)
11. [Definition of Done](#11-definition-of-done)
12. [Project Timeline](#12-project-timeline)
13. [Deliverables](#13-deliverables)
14. [Maintenance Plan](#14-maintenance-plan)
15. [Future Roadmap](#15-future-roadmap)

---

## 1. Project Overview

### 1.1 Project Objective

Build the **Agentic AI-Based University Workflow Automation System** — a Multi-Agent Student Support Platform for **Sindh Madressatul Islam University (SMIU)** that automates university workflows (admissions, examinations, general inquiries) end to end. The platform routes, processes, and resolves real student requests through a LangGraph-coordinated multi-agent system grounded in a RAG knowledge base, instead of acting as a simple chatbot (PROJECT_RULES.md Project Goal).

### 1.2 Scope

**Phase 1 (current FYP) — in scope:**

- Landing page, About, Contact pages.
- JWT-based authentication (login/registration).
- Student dashboard, AI chat interface, chat history, profile and settings.
- Coordinator, Admission, Examination, and FAQ agents.
- RAG over a FAISS vector store using LangChain.
- SQLite for development; PostgreSQL-ready production schema (16 tables per DATABASE_DESIGN.md).

**Future scope — explicitly out of Phase 1 (placeholders only):**

- Finance, Registration, Library, Hostel, Scholarship, IT Support agents.
- ERP/LMS integration, voice assistant, mobile app, multilingual support.
- Admin panel (future phase; documented but not implemented).

(PROJECT_RULES.md Project Scope, Future Scope; PROJECT_RULES.md AI Development Roadmap)

### 1.3 Implementation Strategy

- **Documentation-driven** — every implementation step is derived from the architecture source documents (see §1 of each; PROJECT_RULES.md Documentation Rules).
- **Feature-first, vertical slices** — features are built end to end (backend + AI + frontend) rather than one entire layer at a time, while respecting the phased dependency order.
- **Test-with-code** — tests are written with each feature (Shift Left, TESTING_STRATEGY.md §1.2).
- **Git-workflow disciplined** — branches, conventional commits, and PRs per DEVELOPMENT_WORKFLOW.md §8–11.
- **Environment-isolated** — development on SQLite with mocked LLM; staging/production later (DEVELOPMENT_WORKFLOW.md §16; TESTING_STRATEGY.md §27).

### 1.4 Development Methodology

- **Incremental and Agile (Scrum-like)** — work in short iterations (weeks), each delivering a working, tested increment.
- Backlog is defined by this plan (§4); sprints map to the weekly roadmap (§7).
- Each increment passes quality gates (§10) before the next begins.
- Continuous feedback: supervisor reviews at each milestone (§6).

### 1.5 Success Criteria

| Criterion | Measure |
| --------- | ------- |
| Functional completeness | All Phase 1 scope features implemented per the architecture docs. |
| AI quality | Evaluation metrics meet AI_ARCHITECTURE.md §38 thresholds (near-zero hallucination, high routing/retrieval/citation accuracy). |
| Quality | All quality gates green (TESTING_STRATEGY.md §31); coverage standards met (§29). |
| Research-grade documentation | Complete doc set, testing reports, and evidence for the FYP report. |
| Deployment readiness | Dockerized stack deploys cleanly to staging; operational checklists pass (DEPLOYMENT.md §32–33). |

---

## 2. Development Principles

| Principle | Application |
| --------- | ----------- |
| **Modular development** | Small, independent, well-bounded modules with one responsibility each (PROJECT_RULES.md Project Principles; BACKEND_ARCHITECTURE.md §2). |
| **Feature-first implementation** | Build features end to end; each feature is complete, tested, and documented before the next (DEVELOPMENT_WORKFLOW.md §7). |
| **Reusable components** | Reuse shared UI components (shadcn/ui + feature composites), services, utilities, and prompts before writing anything new (ui-ux-design.md §25; PROJECT_RULES.md Development Rules). |
| **Documentation-driven development** | Architecture docs are updated before code when they define behavior; docs are part of Definition of Done (DEVELOPMENT_WORKFLOW.md §18). |
| **Test-driven mindset** | Tests written with the code; every fix protected by a regression test (TESTING_STRATEGY.md §1.2, §20). |
| **Git workflow** | Feature branches, conventional commits, PR review, no direct pushes to `main`/`develop` (DEVELOPMENT_WORKFLOW.md §8–10). |
| **Code review process** | Every non-trivial change reviewed for readability, architecture compliance, security, performance, testing, documentation (DEVELOPMENT_WORKFLOW.md §12). |

---

## 3. Project Phases

Each phase must complete its deliverables and pass its completion criteria (and the quality gates in §10) before the next phase begins. Phases follow the order mandated by PROJECT_RULES.md Project Workflow.

---

### Phase 1 — Project Setup

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Initialize the repository, tooling, and CI foundation so every later phase builds on a stable base. |
| **Deliverables** | Standard folder structure (PROJECT_RULES.md), environment templates, Docker skeleton, CI skeletons, `.gitignore`, doc set acknowledged. |
| **Dependencies** | None (first phase). |
| **Expected output** | A clean, versioned repository matching the standard project layout; environment templates for frontend/backend/AI. |
| **Completion criteria** | Repo structure matches PROJECT_RULES.md; `.env.example` present; CI runs lint/type-check/build placeholders; docs/index present. |

---

### Phase 2 — Backend Foundation

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Stand up the FastAPI application with the layered architecture and cross-cutting concerns. |
| **Deliverables** | App shell (api/core/models/schemas/services/middleware), settings, DI, logging, exception handling, API versioning (`/api/v1`), health endpoints. |
| **Dependencies** | Phase 1. |
| **Expected output** | A running FastAPI service exposing health endpoints and the versioned API root (BACKEND_ARCHITECTURE.md §6, §15–17; API_SPECIFICATION.md §24). |
| **Completion criteria** | Health endpoints respond; unified error envelope works; logging/correlation IDs in place; Pydantic v2 validation configured; structure matches BACKEND_ARCHITECTURE.md. |

---

### Phase 3 — Database

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Implement the complete schema, migrations, and seeds. |
| **Deliverables** | SQLAlchemy 2.0 models for all 16 tables, Alembic migrations, seed data, repository pattern foundation. |
| **Dependencies** | Phase 2 (session management, DI). |
| **Expected output** | A migrated database with all tables/constraints/indexes per DATABASE_DESIGN.md §5–11 and §28; seedable sample data. |
| **Completion criteria** | Migrations apply cleanly; constraints/relationships/indexes verified; seed data loads; DB tests pass (TESTING_STRATEGY.md §7). |

---

### Phase 4 — Authentication

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Implement the complete identity lifecycle. |
| **Deliverables** | Register, login, JWT issue/refresh, logout, password reset, email verification, sessions, RBAC. |
| **Dependencies** | Phase 3 (users, students, sessions tables). |
| **Expected output** | A student can register, verify, log in, and access protected endpoints; RBAC enforced (API_SPECIFICATION.md §3–5; BACKEND_ARCHITECTURE.md §9–10). |
| **Completion criteria** | Auth/security test suite passes (§9 in TESTING_STRATEGY.md); protected routes reject unauthenticated/unauthorized access. |

---

### Phase 5 — Frontend Foundation

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Stand up the Next.js app with the design system and shared components. |
| **Deliverables** | Next.js 15 app, Tailwind tokens, shadcn/ui initialization, base layouts, navigation shell, design-token primitives (ui-ux-design.md §7–10, §24). |
| **Dependencies** | Phase 1. |
| **Expected output** | A responsive app shell with shared components, tokens, and public pages (landing, about, contact) per ui-ux-design.md §15. |
| **Completion criteria** | Pages render at all breakpoints; tokens/components comply with ui-ux-design.md; a11y and responsive checks pass (§17 in TESTING_STRATEGY.md). |

---

### Phase 6 — Student Dashboard

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Build the authenticated student experience. |
| **Deliverables** | Login/register UI, student dashboard with stats/activity, protected routes, profile view (read). |
| **Dependencies** | Phase 4 (auth) + Phase 5 (frontend foundation). |
| **Expected output** | A student can log in, land on a personal dashboard, and see their activity (ui-ux-design.md §16). |
| **Completion criteria** | Auth UI flows tested; dashboard states (loading/empty/error) implemented per ui-ux-design.md §29, §34–35. |

---

### Phase 7 — Request Management

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Implement the workflow request system (create, track, status). |
| **Deliverables** | Request APIs (API_SPECIFICATION.md §18), service layer for lifecycle/status transitions, request timeline, request UI in dashboard. |
| **Dependencies** | Phase 4 (auth) + Phase 6 (dashboard). |
| **Expected output** | A student can submit a request and track its status transitions (DATABASE_DESIGN.md §17–18; ui-ux-design.md §17). |
| **Completion criteria** | Request lifecycle tests pass; timeline append-only behavior verified; notifications groundwork documented. |

---

### Phase 8 — AI Foundation

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Stand up the AI service: agents, LangGraph workflow, prompts, guardrails. |
| **Deliverables** | `ai/` structure, Coordinator + Admission + Examination + FAQ agents, LangGraph graph, versioned prompts, safety rules and guardrails. |
| **Dependencies** | Phase 2 (AI integration boundary, BACKEND_ARCHITECTURE.md §20). |
| **Expected output** | A runnable agent workflow that detects intent and routes to the correct specialist (AI_ARCHITECTURE.md §9, §11). |
| **Completion criteria** | Agent routing tested (TESTING_STRATEGY.md §10–11); prompts versioned; guardrails enforced and logged. |

---

### Phase 9 — RAG Implementation

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Build the knowledge base ingestion and retrieval pipeline. |
| **Deliverables** | Knowledge ingestion, chunking, embeddings (Sentence Transformers), FAISS index, retriever, context builder, citations. |
| **Dependencies** | Phase 8 (AI service); Phase 3 (knowledge tables). |
| **Expected output** | Retrieval works against a real FAISS index with category scoping and citations (AI_ARCHITECTURE.md §14–19; BACKEND_ARCHITECTURE.md §21). |
| **Completion criteria** | RAG tests pass (TESTING_STRATEGY.md §12); golden retrieval set established; knowledge coverage baseline measured. |

---

### Phase 10 — AI Chat System

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Wire the full chat experience end to end. |
| **Deliverables** | Chat APIs (API_SPECIFICATION.md §20–22), conversation management, chat UI (ui-ux-design.md §13, §36), memory integration, feedback. |
| **Dependencies** | Phase 8 (agents) + Phase 9 (RAG) + Phase 6 (dashboard/UI). |
| **Expected output** | A student can chat with the assistant, receive grounded answers with citations, resume history, and rate responses. |
| **Completion criteria** | Conversation lifecycle tests pass (TESTING_STRATEGY.md §14); AI evaluation metrics meet thresholds (AI_ARCHITECTURE.md §38). |

---

### Phase 11 — Notifications

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Implement in-app notifications for request/status events. |
| **Deliverables** | Notification APIs (API_SPECIFICATION.md §19), notification service, notification UI in dashboard (ui-ux-design.md §18). |
| **Dependencies** | Phase 7 (requests) + Phase 6 (dashboard). |
| **Expected output** | Students receive in-app notifications on relevant events with priority ordering. |
| **Completion criteria** | Notification CRUD/read-state tests pass; priority model matches ui-ux-design.md §18. |

---

### Phase 12 — Profile & Settings

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Complete the student self-service account surface. |
| **Deliverables** | Profile read/update APIs (API_SPECIFICATION.md §17), settings UI, owner-scoped updates with optimistic concurrency. |
| **Dependencies** | Phase 4 (auth) + Phase 6 (dashboard). |
| **Expected output** | A student can view and update their profile and settings within owner scope. |
| **Completion criteria** | Owner-scoping verified (DATABASE_DESIGN.md §30); version-conflict behavior (409) implemented and tested. |

---

### Phase 13 — Testing

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Complete the full test suite, AI evaluation harness, and performance validation. |
| **Deliverables** | Full unit/integration/API/E2E suites, AI golden eval harness, load/performance runs, coverage reports, UAT with students. |
| **Dependencies** | All functional phases. |
| **Expected output** | A green, reproducible test suite meeting coverage standards (TESTING_STRATEGY.md §29) and evaluation baselines (§31). |
| **Completion criteria** | All quality gates green (TESTING_STRATEGY.md §31); UAT feedback resolved (§22). |

---

### Phase 14 — Deployment

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Containerize and deploy the platform. |
| **Deliverables** | Docker images (frontend/backend/worker/db), Docker Compose stacks, reverse proxy, environment config, deployment runbook. |
| **Dependencies** | Phase 13 (validated release candidate). |
| **Expected output** | A staging deployment matching DEPLOYMENT.md §4 and §28; smoke tests pass. |
| **Completion criteria** | Operational + production readiness checklists pass (DEPLOYMENT.md §32–33). |

---

### Phase 15 — Final Optimization

| Aspect | Detail |
| ------ | ------ |
| **Objective** | Polish performance, UX, documentation, and final evidence. |
| **Deliverables** | Performance tuning (caching, queries, tokens), final accessibility pass, documentation finalization, FYP report evidence. |
| **Dependencies** | Phase 14. |
| **Expected output** | A production-ready platform meeting budgets (API_SPECIFICATION.md §36) and Definition of Done (§11). |
| **Completion criteria** | Final milestone checklist (§6) and Definition of Done for the entire project (§11.4) met; final submission ready. |

---

## 4. Detailed Implementation Tasks

Each phase decomposes into actionable tasks. Every task is a unit of work tracked via the Git workflow (§2; DEVELOPMENT_WORKFLOW.md §6) with tests written alongside.

### Backend

- [ ] Configure FastAPI application factory and ASGI entrypoint.
- [ ] Configure settings (Pydantic Settings) with environment separation.
- [ ] Configure structured logging with correlation IDs.
- [ ] Implement centralized exception handling + uniform error envelope.
- [ ] Implement dependency injection (request-scoped session, services).
- [ ] Set up API versioning under `/api/v1`.
- [ ] Implement health endpoints (`/health/live`, `/health/ready`, `/health`, `/health/version`).
- [ ] Implement middleware (CORS, security headers, request logging).
- [ ] Implement background tasks (embeddings, indexing, notifications, retention).
- [ ] Implement file upload handling (validation, checksums, safe filenames).

### Database

- [ ] Define SQLAlchemy 2.0 base + session management.
- [ ] Create models for all 16 tables per DATABASE_DESIGN.md §12–25.
- [ ] Define relationships, constraints, and indexes (§8–11).
- [ ] Configure Alembic; generate initial migration.
- [ ] Add seed data (departments, sample knowledge, sample users).
- [ ] Implement repository pattern foundation (§12 in BACKEND_ARCHITECTURE.md).
- [ ] Implement soft delete and ownership scoping.
- [ ] Implement optimistic concurrency (`version` fields) and audit-write patterns.

### Authentication

- [ ] Implement password hashing (bcrypt/argon2 family).
- [ ] Implement JWT access/refresh token issuance.
- [ ] Implement registration with email verification.
- [ ] Implement login with rate limiting.
- [ ] Implement refresh/rotation and revocation (sessions table).
- [ ] Implement password reset flow.
- [ ] Implement RBAC authorization (student/admin) + owner scoping.
- [ ] Implement logout and session invalidation.

### Frontend

- [ ] Set up Next.js 15 app (App Router).
- [ ] Configure Tailwind CSS + design tokens per ui-ux-design.md §24.
- [ ] Initialize shadcn/ui component library.
- [ ] Build base layouts and navigation shell (ui-ux-design.md §9).
- [ ] Implement public pages (landing, about, contact) per §15.
- [ ] Implement login/register pages and auth state.
- [ ] Build student dashboard (stats, activity) per §12, §16.
- [ ] Build AI chat interface (states, streaming, sources) per §13, §36.
- [ ] Build chat history/resume UI.
- [ ] Build request submission/tracking UI per §17.
- [ ] Build notifications UI per §18.
- [ ] Build profile/settings UI.
- [ ] Implement empty/loading/error states everywhere (§29, §34–35).

### AI

- [ ] Set up `ai/` service structure (agents, graphs, prompts, tools, memory, rag).
- [ ] Implement LangGraph graph (nodes, edges, state) per AI_ARCHITECTURE.md §11–12.
- [ ] Implement Coordinator Agent (intent detection, routing) per §9.
- [ ] Implement Admission Agent.
- [ ] Implement Examination Agent.
- [ ] Implement FAQ Agent.
- [ ] Implement versioned prompts in `ai/prompts/` per PROJECT_RULES.md.
- [ ] Implement guardrails and safety rules per §25–26.
- [ ] Implement conversation memory (short/long-term) per §21.
- [ ] Implement agent handoff and error recovery per §23–24.

### RAG

- [ ] Implement document ingestion and chunking.
- [ ] Configure Sentence Transformers embeddings.
- [ ] Build FAISS index + persistence.
- [ ] Implement retriever with metadata filtering and top-K.
- [ ] Implement context builder within token budget.
- [ ] Implement citation generation/dedup (`ai_sources`).
- [ ] Implement knowledge re-indexing as a background job.
- [ ] Establish golden retrieval/eval sets for regression.

### Testing

- [ ] Set up pytest for backend/AI; component test setup for frontend.
- [ ] Write unit tests (services, schemas, prompts, helpers).
- [ ] Write integration tests (service + repository + DB).
- [ ] Write API contract tests (status, errors, pagination/filter/sort).
- [ ] Write auth/security tests.
- [ ] Write AI tests (routing, grounding, citations, guardrails).
- [ ] Write RAG tests (retrieval golden sets, coverage).
- [ ] Write UI component/E2E tests.
- [ ] Set up load/performance tests.
- [ ] Generate coverage reports per TESTING_STRATEGY.md §29.

### Deployment

- [ ] Create Dockerfiles (frontend, backend, worker) per BACKEND_ARCHITECTURE.md §27.
- [ ] Create Docker Compose stacks (dev + prod).
- [ ] Configure reverse proxy + HTTPS (DEPLOYMENT.md §14–15).
- [ ] Configure persistent volumes + backups.
- [ ] Set up environment variable injection + secrets management.
- [ ] Configure CI pipelines (lint, type-check, test, build) per DEVELOPMENT_WORKFLOW.md §28.5.
- [ ] Configure monitoring + health-check wiring.
- [ ] Run operational and production readiness checklists (DEPLOYMENT.md §32–33).

---

## 5. Feature Dependency Matrix

```
Authentication
      │
      ▼
Student Dashboard ───────────► Profile & Settings
      │
      ▼
Request Management ──────────► Notifications
      │
      ▼
AI Foundation (agents) ──────► RAG Implementation
      │                              │
      └────────────┬─────────────────┘
                   ▼
              AI Chat System
                   │
                   ▼
            Feedback / Evaluation
```

| Feature | Depends on | Needed by |
| ------- | ---------- | --------- |
| Authentication | Database (users/sessions) | Dashboard, Requests, Chat, Profile |
| Student Dashboard | Auth, Frontend foundation | Requests UI, Chat UI, Notifications UI |
| Request Management | Dashboard, Auth | Notifications, Request UI |
| Notifications | Request Management, Dashboard | — |
| AI Foundation | Backend foundation (AI boundary) | RAG, AI Chat |
| RAG Implementation | AI Foundation, Knowledge tables | AI Chat |
| AI Chat System | AI Foundation + RAG + Dashboard | Feedback/Evaluation |
| Profile & Settings | Auth, Dashboard | — |
| Testing | All functional features | Deployment |
| Deployment | Testing (release candidate) | Final submission |

**Ordering rule:** a feature never starts until its dependencies are complete and their quality gates are green (§10).

---

## 6. Milestones

| Milestone | Exit criteria |
| --------- | ------------- |
| **Project Initialized** | Repo structure, env templates, CI skeleton, doc set in place (Phase 1). |
| **Backend Complete** | FastAPI foundation, health, middleware, error handling, DI working (Phase 2). |
| **Database Complete** | All 16 tables, migrations, seeds, repository foundation (Phase 3). |
| **Authentication Complete** | Full identity lifecycle + RBAC implemented and tested (Phase 4). |
| **Frontend MVP Complete** | Design system, public pages, auth UI, dashboard shell (Phases 5–6). |
| **AI Integration Complete** | Agents + LangGraph workflow + guardrails working (Phase 8). |
| **RAG Complete** | Ingestion, retrieval, citations working with golden sets (Phase 9). |
| **Chat Complete** | Full chat experience + memory + feedback working (Phase 10). |
| **Testing Complete** | All suites green, eval baselines captured, UAT done (Phase 13). |
| **Production Ready** | Staging deployment validated; checklists pass (Phase 14–15). |

Each milestone is reviewed with the supervisor; a milestone is declared complete only on verified exit criteria (DEVELOPMENT_WORKFLOW.md §5).

---

## 7. Weekly Development Roadmap

The roadmap schedules all 15 phases across 12 weeks. It is a target plan — the quality gates (§10) override the calendar if a phase is not complete.

### Week 1 — Project Setup & Architecture Review

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Initialize repository; confirm architecture understanding. |
| **Tasks** | Clone/init repo; apply standard folder structure; create `.env.example`; scaffold CI; read and acknowledge all architecture docs. |
| **Deliverables** | Project skeleton, environment templates, CI skeleton, doc review notes. |

### Week 2 — Backend Foundation

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Running FastAPI service with cross-cutting concerns. |
| **Tasks** | FastAPI app factory; settings; logging; exception handling; DI; API versioning; health endpoints. |
| **Deliverables** | Working backend shell + health endpoints + backend unit tests. |

### Week 3 — Database

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Complete schema and migrations. |
| **Tasks** | Models for 16 tables; relationships/constraints/indexes; Alembic initial migration; seeds; repository foundation. |
| **Deliverables** | Migrated, seeded database + DB tests (TESTING_STRATEGY.md §7). |

### Week 4 — Authentication

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Full identity lifecycle. |
| **Tasks** | Hashing; JWT issue/refresh; register+verify; login+rate limit; refresh rotation; password reset; RBAC; owner scoping. |
| **Deliverables** | Auth endpoints + auth/security test suite green. |

### Week 5 — Frontend Foundation & Dashboard

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Design system + student dashboard shell. |
| **Tasks** | Next.js setup; Tailwind + tokens; shadcn/ui init; layouts/navigation; public pages; login/register UI; dashboard shell. |
| **Deliverables** | Responsive app shell + public pages + dashboard prototype. |

### Week 6 — Request Management & Notifications

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Request workflow + notifications. |
| **Tasks** | Request APIs + lifecycle service; request UI; timeline; notification APIs + UI. |
| **Deliverables** | Request submission/tracking + notifications working; tests pass. |

### Week 7 — AI Foundation

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Agents + LangGraph workflow + guardrails. |
| **Tasks** | AI service structure; LangGraph graph; Coordinator + Admission + Examination + FAQ agents; versioned prompts; guardrails. |
| **Deliverables** | Runnable agent workflow with routing tests. |

### Week 8 — RAG Implementation

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Working retrieval pipeline. |
| **Tasks** | Ingestion; chunking; embeddings; FAISS index; retriever; context builder; citations; re-index job. |
| **Deliverables** | Real retrieval over knowledge base + golden retrieval sets. |

### Week 9 — AI Chat System

| Aspect | Detail |
| ------ | ------ |
| **Goals** | End-to-end chat experience. |
| **Tasks** | Chat APIs; conversation management; chat UI (states, streaming, sources); memory; feedback wiring. |
| **Deliverables** | Working chat with grounded answers, citations, history, ratings. |

### Week 10 — Profile & Settings, Notifications Polish

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Complete self-service surface + UI polish. |
| **Tasks** | Profile/settings APIs + UI; optimistic concurrency; notification polish; empty/loading/error state completion. |
| **Deliverables** | Complete student portal feature set. |

### Week 11 — Testing & Evaluation

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Full suite + evaluation baselines. |
| **Tasks** | Complete unit/integration/API/E2E suites; AI eval harness + golden sets; coverage reports; performance runs; UAT prep. |
| **Deliverables** | Green suite, coverage report, AI eval baselines, UAT results. |

### Week 12 — Deployment & Final Optimization

| Aspect | Detail |
| ------ | ------ |
| **Goals** | Staging deployment + final polish + submission prep. |
| **Tasks** | Docker images; compose stacks; reverse proxy; env/secrets; CI/CD; smoke validation; performance/UX polish; documentation finalization; FYP report evidence. |
| **Deliverables** | Validated staging deployment; production-readiness checklists pass; final submission package. |

---

## 8. Development Checklist

Trackable completion checklists per area. Each box must be checked with verified evidence before the corresponding quality gate passes (§10).

### Backend

- [ ] FastAPI app factory and entrypoint.
- [ ] Settings with environment separation.
- [ ] Structured logging with correlation IDs.
- [ ] Centralized exception handling + uniform error envelope.
- [ ] Dependency injection (session, services).
- [ ] API versioning under `/api/v1`.
- [ ] Health endpoints.
- [ ] Middleware (CORS, headers, request logging).
- [ ] Background tasks.
- [ ] File upload handling.
- [ ] No business logic in routers; repositories used consistently.

### Database

- [ ] All 16 tables modeled.
- [ ] Relationships, constraints, indexes defined.
- [ ] Alembic migrations apply cleanly.
- [ ] Seed data loads.
- [ ] Repository pattern implemented.
- [ ] Soft delete + ownership scoping.
- [ ] Optimistic concurrency + audit-write patterns.
- [ ] Transactions and rollback verified (DATABASE_DESIGN.md §34).

### Frontend

- [ ] Next.js 15 app running.
- [ ] Tailwind tokens per ui-ux-design.md §24.
- [ ] shadcn/ui initialized.
- [ ] Layouts and navigation shell.
- [ ] Public pages.
- [ ] Login/register UI.
- [ ] Student dashboard.
- [ ] AI chat interface (states, streaming, sources).
- [ ] Chat history/resume.
- [ ] Request submission/tracking UI.
- [ ] Notifications UI.
- [ ] Profile/settings UI.
- [ ] Empty/loading/error states everywhere.
- [ ] Responsive at all breakpoints; a11y passes.

### AI

- [ ] AI service structure.
- [ ] LangGraph graph implemented.
- [ ] Coordinator Agent.
- [ ] Admission Agent.
- [ ] Examination Agent.
- [ ] FAQ Agent.
- [ ] Versioned prompts.
- [ ] Guardrails + safety rules.
- [ ] Conversation memory.
- [ ] Agent handoff + error recovery.

### Testing

- [ ] Backend unit tests.
- [ ] Backend integration tests.
- [ ] API contract tests.
- [ ] Auth/security tests.
- [ ] AI tests (routing, grounding, citations).
- [ ] RAG tests (golden sets, coverage).
- [ ] Frontend component tests.
- [ ] E2E critical journeys.
- [ ] Load/performance tests.
- [ ] Coverage reports per TESTING_STRATEGY.md §29.

### Deployment

- [ ] Dockerfiles for all services.
- [ ] Docker Compose stacks (dev + prod).
- [ ] Reverse proxy + HTTPS.
- [ ] Persistent volumes + backups.
- [ ] Environment variables + secrets management.
- [ ] CI pipelines.
- [ ] Monitoring + health-check wiring.
- [ ] Operational checklist passed (DEPLOYMENT.md §32).
- [ ] Production readiness checklist passed (DEPLOYMENT.md §33).

### Documentation

- [ ] All architecture docs reviewed and current.
- [ ] API docs current (API_SPECIFICATION.md §30).
- [ ] README accurate.
- [ ] Deployment/ops docs current.
- [ ] Test reports and evaluation evidence archived.
- [ ] FYP report materials finalized.

---

## 9. Risk Management

| Category | Risk | Mitigation |
| -------- | ---- | ---------- |
| **Technical** | Environment drift (works locally, fails in CI) | Reproducible environments + isolated config (DEVELOPMENT_WORKFLOW.md §16; TESTING_STRATEGY.md §27). |
| **Technical** | Layer violations creep into code | Code review gate enforces architecture (DEVELOPMENT_WORKFLOW.md §12); architecture docs are the source. |
| **Technical** | Flaky tests erode trust | Deterministic, isolated tests; flake quarantine (TESTING_STRATEGY.md §1.5, §20.3). |
| **AI** | Hallucination / unsupported claims | Grounding rules, post-processing checks, evaluation metrics (AI_ARCHITECTURE.md §18.4, §38). |
| **AI** | LLM nondeterminism breaks tests | Mocked/gated LLM in automated suites; golden fixtures (TESTING_STRATEGY.md §23.2). |
| **AI** | Embedding/model change breaks retrieval | Golden retrieval sets; re-embed on change (TESTING_STRATEGY.md §12.2). |
| **Database** | Migration drift / data loss | Migration tests on empty + existing DBs; backups + restore drills (DATABASE_DESIGN.md §29; TESTING_STRATEGY.md §7.5). |
| **Database** | Concurrency/transaction bugs | Transaction + concurrency tests (DATABASE_DESIGN.md §34; TESTING_STRATEGY.md §7.4). |
| **Deployment** | Post-deploy failures | Smoke tests + rollback strategy + readiness checklists (DEPLOYMENT.md §28–30, §32–33). |
| **Deployment** | Secret exposure | Secrets never committed; CI secret scan; rotation policy (DEVELOPMENT_WORKFLOW.md §26; DEPLOYMENT.md §13). |
| **Schedule** | Milestone slip | Quality gates gate progress; weekly cadence; scope discipline (Phase 1 scope only) (PROJECT_RULES.md Project Scope). |
| **Schedule** | Scope creep | Future scope is explicit non-goal in Phase 1 (PROJECT_RULES.md Future Scope; §1.2). |

**Process:** risks are reviewed weekly; new risks are added and mitigations tracked to closure (DEVELOPMENT_WORKFLOW.md §31).

---

## 10. Quality Gates

Mandatory checks before moving to the next phase (or merging to `develop`). A gate failure blocks progress (DEVELOPMENT_WORKFLOW.md §32; TESTING_STRATEGY.md §31).

| Gate | Check |
| ---- | ----- |
| **Code review** | Review passed per DEVELOPMENT_WORKFLOW.md §12; architecture compliance verified. |
| **Testing** | All relevant automated suites green; coverage standards met (TESTING_STRATEGY.md §29). |
| **Documentation update** | Docs updated with the change (DEVELOPMENT_WORKFLOW.md §18). |
| **Performance verification** | Budgets met; no regressions (TESTING_STRATEGY.md §31.3). |
| **Security verification** | Security checks pass; no unresolved high findings (TESTING_STRATEGY.md §31.4). |
| **Accessibility verification** | WCAG AA, keyboard nav, screen-reader basics verified (TESTING_STRATEGY.md §17). |

---

## 11. Definition of Done

### 11.1 Feature

- Implemented per the architecture docs, coding standards, and folder rules.
- Tests written with the feature; all relevant suites green.
- Documentation updated in the same change.
- Review approved and PR merged.
- Performance/security no regressions.

### 11.2 Module

- All contained features are Done (§11.1).
- Module tests green; module-level coverage met.
- Module documented (inline + docs as applicable).

### 11.3 Phase

- All phase deliverables produced.
- Phase completion criteria met (§3).
- Quality gates passed (§10).
- Phase milestone reviewed with the supervisor (§6).

### 11.4 Entire Project

- All Phase 1 scope features complete and Done.
- All quality gates green; production readiness checklists pass (DEPLOYMENT.md §32–33).
- Documentation set complete and current.
- AI evaluation baselines meet AI_ARCHITECTURE.md §38 targets.
- FYP deliverables (code, docs, test reports, deployment config, presentation, final report) complete.

---

## 12. Project Timeline

High-level sequence from start to final deployment (12 weeks):

| Week | Phase(s) | Milestone |
| ---- | -------- | --------- |
| 1 | Phase 1 — Project Setup | Project Initialized |
| 2 | Phase 2 — Backend Foundation | Backend Complete |
| 3 | Phase 3 — Database | Database Complete |
| 4 | Phase 4 — Authentication | Authentication Complete |
| 5 | Phases 5–6 — Frontend Foundation + Dashboard | Frontend MVP Complete |
| 6 | Phase 7 — Request Management (+ notifications groundwork) | Request workflow |
| 7 | Phase 8 — AI Foundation | AI Integration Complete |
| 8 | Phase 9 — RAG Implementation | RAG Complete |
| 9 | Phase 10 — AI Chat System | Chat Complete |
| 10 | Phases 11–12 — Notifications + Profile & Settings | Portal feature set complete |
| 11 | Phase 13 — Testing | Testing Complete |
| 12 | Phases 14–15 — Deployment + Final Optimization | Production Ready |

Timeline rule: weeks are targets; the quality gates (§10) and Definition of Done (§11) determine actual completion.

---

## 13. Deliverables

| Deliverable | Contents |
| ----------- | -------- |
| **Source code — frontend** | Next.js app per ui-ux-design.md. |
| **Source code — backend** | FastAPI layered API per BACKEND_ARCHITECTURE.md. |
| **Database** | Models, migrations, seeds per DATABASE_DESIGN.md. |
| **AI System** | Agents, LangGraph, RAG, prompts, guardrails per AI_ARCHITECTURE.md. |
| **Documentation** | Complete doc set (see §19 in README.md) — architecture, API, testing, workflow, deployment, plan. |
| **Testing reports** | Suite results, coverage reports, AI evaluation baselines, load/performance results, UAT findings. |
| **Deployment configuration** | Dockerfiles, compose stacks, reverse proxy config, env templates, CI pipelines. |
| **Presentation** | FYP demonstration and defense materials. |
| **Final report** | Research report with architecture rationale, metrics, and evidence (AI_ARCHITECTURE.md §38.3). |

---

## 14. Maintenance Plan

Post-development activities keep the platform healthy after delivery (DEVELOPMENT_WORKFLOW.md §3.6, §31).

| Activity | Approach |
| -------- | -------- |
| **Bug fixes** | Tracked via bug workflow; fixes protected by regression tests (DEVELOPMENT_WORKFLOW.md §21). |
| **Performance improvements** | Continuous perf monitoring; optimize against budgets (DEPLOYMENT.md §25, §31). |
| **Documentation updates** | Docs updated with every change (DEVELOPMENT_WORKFLOW.md §18). |
| **Knowledge base updates** | New documents ingested/versioned; re-index + retrieval regression (AI_ARCHITECTURE.md §36; TESTING_STRATEGY.md §13). |
| **Future enhancements** | Implemented via the roadmap (§15) through the same phased workflow and gates. |

---

## 15. Future Roadmap

Future improvements beyond Phase 1 (PROJECT_RULES.md Future Scope; AI Development Roadmap; DEVELOPMENT_WORKFLOW.md §36; DEPLOYMENT.md §34).

| Capability | Notes |
| ---------- | ----- |
| **Admin Panel** | Admin dashboard for students/departments/requests (API_SPECIFICATION.md §25). |
| **Additional AI Agents** | Finance, Registration, Scholarship, Library, Hostel, IT Support. |
| **Voice Assistant** | Voice input/output for the assistant. |
| **OCR** | Document intake via OCR for the knowledge base. |
| **Email Integration** | Notifications/verification via email (outbox pattern). |
| **Analytics Dashboard** | Usage analytics from monitoring data (AI_ARCHITECTURE.md §31.6). |
| **Multi-language Support** | Multilingual UI and assistant. |
| **Mobile Application** | Same versioned REST surface (API_SPECIFICATION.md §39). |
| **Real-time Notifications** | WebSockets/SSE live updates (API_SPECIFICATION.md §39). |
| **Advanced AI Capabilities** | Re-ranking, hybrid search, streaming responses, broader model support. |

**Roadmap rules:** future items are not built in Phase 1; each is planned through this implementation workflow (phases → tasks → tests → release) when its phase begins (DEVELOPMENT_WORKFLOW.md §36).

---

## Important

This document is the **permanent implementation plan** and the **single source of truth for the project implementation sequence**.

It must be read together with:

- **PROJECT_RULES.md** — master project rules (phases, scope, coding standards, DoD).
- **docs/architecture/ui-ux-design.md** — the only design source for the frontend.
- **docs/architecture/BACKEND_ARCHITECTURE.md** — layered architecture and backend standards.
- **docs/architecture/DATABASE_DESIGN.md** — schema, migrations, transactions, and retention.
- **docs/architecture/AI_ARCHITECTURE.md** — agents, RAG, prompts, and evaluation.
- **docs/architecture/API_SPECIFICATION.md** — endpoint contracts and API standards.
- **docs/architecture/TESTING_STRATEGY.md** — testing strategy and quality gates.
- **docs/architecture/DEVELOPMENT_WORKFLOW.md** — Git workflow, coding standards, releases.
- **docs/architecture/DEPLOYMENT.md** — deployment, monitoring, backup, and recovery.

All implementation activity — phases, tasks, schedules, milestones, and quality checks — must be derived from this document. Any deviation must be corrected before it is accepted.

**This document is planning and documentation only.** It contains no implementation code, no pseudo-code, no Python, no SQL, no Docker configuration, and no scripts. Implementation is derived from these standards, following the project's Development Rules and Definition of Done.

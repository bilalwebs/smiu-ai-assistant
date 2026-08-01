# TESTING_STRATEGY.md

**Agentic AI-Based University Workflow Automation System**
Multi-Agent Student Support Platform — developed for **Sindh Madressatul Islam University (SMIU)**

> Version: 1.0 · Status: Approved Architecture · Last Updated: August 2026 · Owner: Final Year Project Team
> Scope: Single source of truth for the complete testing strategy — testing philosophy, objectives, scope, levels, per-layer test coverage, environments, automation, quality gates, reporting, and risk management.
> Sufficiently detailed that the entire test plan, test suite structure, CI pipelines, and quality-assurance workflows can be derived without additional testing instructions.
> This document is **architecture and documentation only** — it contains no test code, no framework-specific code, no Python, and no SQL.

---

## Table of Contents

1. [Testing Philosophy](#1-testing-philosophy)
2. [Testing Objectives](#2-testing-objectives)
3. [Testing Scope](#3-testing-scope)
4. [Testing Levels](#4-testing-levels)
5. [Frontend Testing](#5-frontend-testing)
6. [Backend Testing](#6-backend-testing)
7. [Database Testing](#7-database-testing)
8. [API Testing](#8-api-testing)
9. [Authentication Testing](#9-authentication-testing)
10. [AI Testing](#10-ai-testing)
11. [LangGraph Testing](#11-langgraph-testing)
12. [RAG Testing](#12-rag-testing)
13. [Knowledge Base Testing](#13-knowledge-base-testing)
14. [Conversation Testing](#14-conversation-testing)
15. [Security Testing](#15-security-testing)
16. [Performance Testing](#16-performance-testing)
17. [UI/UX Testing](#17-uiux-testing)
18. [Browser Compatibility Testing](#18-browser-compatibility-testing)
19. [Device Testing](#19-device-testing)
20. [Regression Testing](#20-regression-testing)
21. [Smoke Testing](#21-smoke-testing)
22. [User Acceptance Testing (UAT)](#22-user-acceptance-testing-uat)
23. [Test Data Management](#23-test-data-management)
24. [Error Testing](#24-error-testing)
25. [Logging & Debugging](#25-logging--debugging)
26. [Monitoring](#26-monitoring)
27. [Test Environment](#27-test-environment)
28. [Test Automation Strategy](#28-test-automation-strategy)
29. [Test Coverage Standards](#29-test-coverage-standards)
30. [Bug Management](#30-bug-management)
31. [Quality Gates](#31-quality-gates)
32. [Test Reporting](#32-test-reporting)
33. [Risk Assessment](#33-risk-assessment)
34. [Future Testing Improvements](#34-future-testing-improvements)

---

## 1. Testing Philosophy

The testing philosophy is the permanent set of principles that governs every test activity in this project. It derives directly from the engineering standards defined in **PROJECT_RULES.md** (Testing Standards, Definition of Done), **docs/architecture/BACKEND_ARCHITECTURE.md** (§26 Testing Strategy), **docs/architecture/AI_ARCHITECTURE.md** (§38 AI Evaluation Metrics), and **docs/architecture/ui-ux-design.md** (§41 UI Testing Checklist).

### 1.1 Quality First

| Rule | Meaning |
| ---- | ------- |
| **Quality is a requirement** | Every feature is incomplete until it is tested; tests are part of the Definition of Done (PROJECT_RULES.md). |
| **Quality is everyone's responsibility** | Developers, testers, and the AI operator share accountability; there is no separate "quality team only" model. |
| **No throwaway quality** | Test activities follow the same production-grade standards as the product code — documented, repeatable, versioned. |
| **Research-grade proof** | Testing itself is an FYP research contribution: metrics, evidence, and methodology are documented and reportable. |

### 1.2 Shift Left Testing

- Testing begins at **requirements and design time**, not after implementation.
- **Design documents are reviewed for testability** before any code is written (testability is a first-class design property).
- **Unit tests are written with the code** — not after; a feature branch is not mergeable without its tests.
- **Early and continuous feedback** — test failures surface within minutes of a commit, not at release time.
- **Cost rationale** — defects found in design are exponentially cheaper to fix than defects found in production; shifting left is an explicit cost-control strategy.

### 1.3 Test Pyramid

The test pyramid defines the *shape* of the suite — many fast, cheap, isolated tests at the base, fewer slow end-to-end tests at the top.

```
            /    E2E     \        Few — slow, expensive, high confidence
           /  Integration \      Some — moderate speed, cross-layer confidence
          /________________\
         /      Unit          \  Many — fast, isolated, cheap
        /______________________\
```

| Layer | Count | Speed | Confidence | Scope |
| ----- | ----- | ----- | ---------- | ----- |
| **Unit** | Many | Fast | Low per test, high in aggregate | Single function/component in isolation |
| **Integration** | Some | Moderate | Moderate | Two or more real layers together (service + repository + DB, route + service) |
| **E2E** | Few | Slow | Highest | Full user journey through the real UI and API stack |

**Rules:**
- Prefer the lowest pyramid level that can validate a behavior.
- A test that must spin up the whole stack for something a unit test could verify is a design smell.
- The pyramid is a guidance ratio, not a fixed count — the "Important" sections of the architecture docs (e.g., BACKEND_ARCHITECTURE.md §26) define the specific levels for this project.

### 1.4 Automation First

- **Automated testing is the default** for all repeatable checks; manual testing is reserved for exploratory, UX, and acceptance activities that cannot be automated.
- **Every change triggers the relevant automated subset** (CI readiness, Section 28).
- **Automation is versioned with the code** — test suites live inside the repository and change with it.
- **Automated regression protection** — anything fixed once must be covered by an automated test so it can never silently regress.
- **Manual effort is minimized** — scripts and tooling exist to make the human test effort small, focused, and valuable.

### 1.5 Reliability

| Rule | Meaning |
| ---- | ------- |
| **Deterministic tests** | Tests must give the same result every run; flaky tests are treated as defects and fixed, never ignored. |
| **Isolated tests** | Tests do not depend on execution order, shared state, or the real production database. |
| **Trusted results** | Only stable, reproducible test results feed quality gates (Section 31). |
| **External dependencies controlled** | Real LLM calls, network, and third-party services are mocked or gated in CI (BACKEND_ARCHITECTURE.md §26). |

### 1.6 Maintainability

- Test suites must be as maintainable as product code — **clear names, clear purpose, no duplication**.
- **Reusable fixtures and helpers** — shared test data, factories, and utilities replace duplicated setup (Section 23).
- **One behavior per test** — tests assert one thing clearly; failures point at the root cause without debugging.
- **Consistent conventions** — test naming, structure, and folder placement follow one documented standard.
- **Tests document the system** — a well-written test suite is living documentation of expected behavior.

### 1.7 Repeatability

- **Deterministic data** — every test run starts from a known, reproducible state.
- **Clean environments** — tests create and tear down their own data; nothing leaks between runs (Section 27).
- **Anyone can run it** — any developer or tester on any machine can reproduce the full suite from the documented commands.
- **Auditable history** — test runs, results, and coverage are recorded and traceable over time (Section 32).
- **Seed-driven repetition** — database and knowledge-base states are reproducible from versioned seed sources (Section 23).

---

## 2. Testing Objectives

The objectives below define *why* the project is tested. Every test activity must map to at least one objective; test coverage is prioritized according to them.

### 2.1 Functional Correctness

- The system does what the specifications say it does — every endpoint, page, workflow, and AI behavior matches the architecture docs.
- User workflows (admission, examination, FAQ requests) complete correctly end to end.
- Business rules, status transitions, validation, and RBAC behave exactly as designed (BACKEND_ARCHITECTURE.md §10, DATABASE_DESIGN.md §17–18).

### 2.2 Performance

- The system meets the response-time budgets defined in **API_SPECIFICATION.md §36** and **AI_ARCHITECTURE.md §31**.
- The system handles expected and peak user concurrency without degradation.
- Performance is verified continuously, not only at release time (Sections 16, 26).

### 2.3 Security

- Authentication, authorization, and data protection behave correctly under attack-like conditions.
- The system resists injection, XSS, CSRF, prompt injection, and data leakage (Section 15).
- PII and secrets are never exposed, logged, or leaked (PROJECT_RULES.md Logging & Monitoring).
- Security is validated both by automated checks and by manual review.

### 2.4 Reliability

- The system fails gracefully: typed errors, friendly messages, retries, and fallbacks per BACKEND_ARCHITECTURE.md §24 and AI_ARCHITECTURE.md §23.
- Recovery paths (network loss, AI failure, database failure) are verified (Section 24).
- High availability of the AI service is measured and protected (AI_ARCHITECTURE.md §38.1 — AI Availability).

### 2.5 AI Quality

- Answers are grounded in the knowledge base, never hallucinated (PROJECT_RULES.md AI Behaviour Rules).
- Agent routing, retrieval, citations, and formatting meet the evaluation metrics defined in AI_ARCHITECTURE.md §38.
- AI regressions are caught by a versioned evaluation harness (AI_ARCHITECTURE.md §38.3).

### 2.6 User Experience

- The interface is usable, accessible, and responsive per ui-ux-design.md.
- All UI states (loading, empty, error) are present and correct (ui-ux-design.md §34–36).
- UAT confirms the system is fit for real SMIU students (Section 22).

---

## 3. Testing Scope

The testing scope defines *what* is tested. It follows the project folder structure and the boundaries defined in **PROJECT_RULES.md** (Project Folder Structure) and the layer ownership rules of **BACKEND_ARCHITECTURE.md**.

### 3.1 Frontend

| Area | In scope |
| ---- | -------- |
| Next.js 15 pages, layouts, and routing | Landing, About, Departments, Contact, Login, Student Portal (Dashboard, AI Chat, Chat History, Profile, Settings) |
| React 19 components (shadcn/ui library + feature composites) | All reusable and feature components |
| Forms, validation, and client state | Login, registration, contact, chat input, profile forms |
| Design-system compliance | Tokens, spacing, radius, shadows, dark-mode readiness |
| UI states | Loading, empty, error, skeleton, streaming (Section 5) |

### 3.2 Backend

- FastAPI routes, services, repositories, and middleware (BACKEND_ARCHITECTURE.md §11–12, §17).
- Business logic for auth, requests, notifications, and knowledge management.
- Validation, exception handling, logging, and error recovery (BACKEND_ARCHITECTURE.md §14–16, §24).
- Background jobs and file uploads (BACKEND_ARCHITECTURE.md §18–19).

### 3.3 Database

- All 16 tables defined in DATABASE_DESIGN.md (§5–11): `users`, `students`, `departments`, `ai_conversations`, `chat_history`, `requests`, `request_timeline`, `notifications`, `documents`, `knowledge_documents`, `knowledge_chunks`, `ai_sources`, `feedback`, `audit_logs`, `agent_logs`, `sessions`.
- Constraints, relationships, indexes, transactions, migrations, and retention (DATABASE_DESIGN.md §8–11, §28, §34–35).

### 3.4 Authentication

- Registration, login, JWT issuance, refresh, revocation, session lifecycle (API_SPECIFICATION.md §3–5; BACKEND_ARCHITECTURE.md §9; DATABASE_DESIGN.md §25).
- Password reset and email verification flows.

### 3.5 AI System

- Coordinator, Admission, Examination, and FAQ agents (PROJECT_RULES.md AI Agents).
- LangGraph graph, nodes, routing, memory, and persistence (AI_ARCHITECTURE.md §11–12, §21–22).
- Prompts, guardrails, safety rules, confidence handling, response formatting (AI_ARCHITECTURE.md §13, §25–28).

### 3.6 APIs

- Every endpoint in API_SPECIFICATION.md §15–24 (student, auth, user, request, notification, chat, AI, knowledge base, health).
- Request/response contracts, status codes, error envelopes, pagination/filtering/sorting, idempotency (API_SPECIFICATION.md §6–12, §34).

### 3.7 Knowledge Base

- Document upload, chunking, metadata, versioning, re-indexing (AI_ARCHITECTURE.md §36; DATABASE_DESIGN.md §20–21).
- FAISS index build, retrieval quality, and knowledge coverage (Section 12–13).

### 3.8 Integrations

- Backend ↔ AI service boundary (BACKEND_ARCHITECTURE.md §20).
- AI service ↔ Gemini 2.5 Flash (via the AI facade, mocked in tests).
- Embedding pipeline (Sentence Transformers) and FAISS retrieval.
- Deployment orchestration (Docker Compose) verified through smoke tests (Section 21).

### 3.9 Out of Scope

- Future-scope agents (Finance, Registration, Library, Hostel, Scholarship, IT Support) are tested only as stubs until implemented (PROJECT_RULES.md Future Scope).
- Non-functional aspects beyond the defined budgets (no formal FMEA/quantified availability SLA in Phase 1).
- External university ERP/LMS systems (future integration; only the outbox pattern boundary is tested).

---

## 4. Testing Levels

Testing is organized into five levels. Each level has a distinct purpose, environment, and entry/exit criteria. These levels map to the pyramid (Section 1.3) and to the test folders under `testing/` (e2e, integration, load).

### 4.1 Unit Testing

| Aspect | Definition |
| ------ | ---------- |
| **Purpose** | Verify a single unit (function, method, component, schema, prompt module) in isolation. |
| **Scope** | Pure business logic, validators, formatters, agent node functions, prompt builders, repository-query helpers, schema defaults. |
| **Isolation** | External boundaries (database, LLM, network, file system) are mocked or stubbed. |
| **Granularity** | One behavior per test; no cross-test ordering dependencies. |
| **Example targets** | Auth password hashing, status-transition rules, pagination helpers, intent-detection parsing, citation de-duplication. |
| **Exit criteria** | All unit tests pass; coverage targets met (Section 29). |

### 4.2 Integration Testing

| Aspect | Definition |
| ------ | ---------- |
| **Purpose** | Verify two or more real layers working together against a real (test) database. |
| **Scope** | Service + repository + database; route + service; AI graph nodes with a mocked LLM; RAG retrieval against a small real index. |
| **Environment** | Dedicated test database (never production); test FAISS index; mocked Gemini 2.5 Flash (BACKEND_ARCHITECTURE.md §26). |
| **Example targets** | Request lifecycle across `requests`/`request_timeline`/`notifications`; auth session creation and revocation; knowledge document ingestion and chunk creation; conversation persistence. |
| **Exit criteria** | Integration suite passes against a clean test database; no cross-contamination of data. |

### 4.3 System Testing

| Aspect | Definition |
| ------ | ---------- |
| **Purpose** | Verify the complete backend + AI system behaves correctly as one deployed unit. |
| **Scope** | Full API surface, background jobs, RAG pipeline, guardrails, and persistence working together. |
| **Environment** | A full stack instance (Docker Compose) with test configuration (Section 27). |
| **Example targets** | A complete request flow (chat → coordinator → specialist → retrieval → response → citations → persistence); knowledge re-index job; notification dispatch. |
| **Exit criteria** | System tests pass on the staging-like stack; smoke suite (Section 21) green. |

### 4.4 End-to-End Testing

| Aspect | Definition |
| ------ | ---------- |
| **Purpose** | Verify complete user journeys through the real UI and API together. |
| **Scope** | Frontend → API → backend → AI → database, as a real user experiences it. |
| **Environment** | E2E stack with seeded test data and a mocked or gated LLM for deterministic assertions. |
| **Example journeys** | Register → login → open chat → ask an admission question → receive grounded answer with citations → rate response; create a request → track status → receive notification. |
| **Exit criteria** | All critical journeys pass on every release candidate (Section 21). |

### 4.5 Acceptance Testing

| Aspect | Definition |
| ------ | ---------- |
| **Purpose** | Confirm the system meets the requirements and is acceptable for delivery. |
| **Scope** | Requirements-level acceptance criteria per feature, plus UAT (Section 22). |
| **Participants** | Development team (internal acceptance) and SMIU students/supervisor (UAT). |
| **Exit criteria** | Formal sign-off against the acceptance criteria; UAT feedback resolved (Section 22.4). |

---

## 5. Frontend Testing

Frontend testing follows the **ui-ux-design.md** document exactly — the design document is the specification the tests verify against (ui-ux-design.md §42 Design Source Policy). The UI Testing Checklist (ui-ux-design.md §41) is the primary reference for the categories below.

### 5.1 Components

| Check | Requirement |
| ----- | ----------- |
| Rendering | Every component renders correctly with its default and edge-case props. |
| Reusability | Components behave identically wherever used — no duplicated, divergent markup (ui-ux-design.md §25, §38). |
| Interactions | Buttons, inputs, dialogs, tabs, menus, and dropdowns behave per spec (Radix-based, ui-ux-design.md §10). |
| Design-token compliance | Colors, spacing, radius, shadows, and typography come only from tokens (ui-ux-design.md §24). |
| Composition | Feature-level composites compose primitives correctly without prop leakage. |
| Copy / export | Chat responses support one-click Copy (ui-ux-design.md §31.4). |

### 5.2 Forms

- Every form matches the form design rules (ui-ux-design.md §11): labels, help text, inline errors, disabled-until-valid, success feedback.
- Client-side validation mirrors server-side validation for every field (PROJECT_RULES.md — validation on both client and server).
- Submit, reset, cancel, and loading-on-submit states are verified.

### 5.3 Validation

- Field-level rules (required, format, length, uniqueness messaging) are tested for valid, invalid, and boundary values.
- Server-rejected submissions surface the server error envelope inline (API_SPECIFICATION.md §8).
- Validation failures never lose user input (drafts preserved).

### 5.4 Navigation

- App Router file conventions (ui-ux-design.md §39) produce the intended routes.
- Navigation system (ui-ux-design.md §9) works at every breakpoint: desktop sidebar, tablet rail, mobile drawer.
- Active states, breadcrumbs, deep links, and back/forward browser behavior are verified.
- Protected routes redirect unauthenticated users to Login and never render protected data.

### 5.5 Responsive Design

- Layouts verified at all breakpoints defined in ui-ux-design.md §8.
- No horizontal overflow; content reflows correctly (ui-ux-design.md §41).
- Mobile: 44px+ targets, sticky chat input, safe areas, drawer navigation (ui-ux-design.md §37).
- Tablet: rail sidebar, 2-column grids; desktop: full sidebar, 4-column stats, content ≤1280px.

### 5.6 Accessibility

- WCAG AA compliance: color contrast, reduced-motion support (ui-ux-design.md §22).
- Full keyboard tab order; arrow keys in menus/tabs; Esc closes overlays; focus never lost (ui-ux-design.md §41).
- Screen readers: semantic HTML, `aria-live` for chat/streaming/toasts, alt text, one `h1` per page (ui-ux-design.md §41).
- Visible 2px focus ring + 4px offset on every focusable element (ui-ux-design.md §22).

### 5.7 Dark Mode Readiness

- UI is built on CSS variables / design tokens — no hardcoded colors (ui-ux-design.md §23, §24).
- Theme swap renders cleanly with correct contrast in both themes.
- Dark-mode readiness is verified even though dark mode ships later (ui-ux-design.md §23).

### 5.8 UI States

| State | Verification |
| ----- | ------------ |
| **Loading** | Spinner/skeleton on every async view; no blank screens (ui-ux-design.md §41). |
| **Skeleton** | Matches final layout 1:1; no layout shift on data arrival (CLS-safe). |
| **Empty state** | Meaningful empty views on every list/dashboard per ui-ux-design.md §34. |
| **Error state** | Friendly message + Retry; no stack traces; drafts preserved (ui-ux-design.md §35). |
| **AI chat states** | All chat lifecycle states verified: idle, thinking/loading, streaming, error/retry, stopped (ui-ux-design.md §36, §31). |
| **Partial/failed uploads** | Upload progress and failure states handled gracefully (API_SPECIFICATION.md §35). |

---

## 6. Backend Testing

Backend testing verifies the layered architecture defined in **BACKEND_ARCHITECTURE.md** — controllers, services, repositories, and middleware — enforcing the layer rules and the project Definition of Done (PROJECT_RULES.md, BACKEND_ARCHITECTURE.md §26).

### 6.1 Business Logic

- Pure business rules verified at the service layer: request status transitions, eligibility rules, notification priority logic, conversation lifecycle rules.
- No business logic lives in routers — tests verify routers only translate HTTP ↔ service calls (BACKEND_ARCHITECTURE.md §25).
- Time-based and state-based logic tested with controlled time/state inputs.

### 6.2 Services

- One service per feature; every public service method is unit-tested for success, validation-failure, and exception paths.
- Service-level workflow tests cover end-to-end behavior of auth flows and the request lifecycle at the service boundary (BACKEND_ARCHITECTURE.md §26).
- Service orchestration (multiple repository calls, single commit) verified per the transaction boundaries (DATABASE_DESIGN.md §34).

### 6.3 Repositories

- Repository query behavior tested against a real test database (CRUD, scoping, transactions) per BACKEND_ARCHITECTURE.md §26.
- Ownership scoping verified: every query is scoped to its owner (student/user) per DATABASE_DESIGN.md §30.
- Soft-delete filters, active-flag filters, and pagination keyset queries verified (DATABASE_DESIGN.md §26, §31).
- Optimistic-concurrency `version` checks verified (DATABASE_DESIGN.md §34.5).

### 6.4 Middleware

- Request-scoped session dependency, correlation-ID propagation, and CORS behavior verified (BACKEND_ARCHITECTURE.md §13, §17).
- Security headers (CSP, frame/cache protections) present on responses (BACKEND_ARCHITECTURE.md §22).
- Middleware never swallows or leaks errors; error responses match the uniform envelope (API_SPECIFICATION.md §8).

### 6.5 Authentication

- Token verification, session lookup, and credential checks verified at the service and middleware boundary (Section 9 covers the flows end to end).
- Hash verification (bcrypt/argon2 family) tested with correct, incorrect, and malformed inputs (BACKEND_ARCHITECTURE.md §22).

### 6.6 Authorization

- RBAC enforced server-side; every role has exactly the permissions defined (BACKEND_ARCHITECTURE.md §10; API_SPECIFICATION.md §4).
- Owner-scoped access: users cannot read/write another user's data (DATABASE_DESIGN.md §30).
- Admin-only routes reject non-admin roles with the correct error shape.
- Default-deny verified: anything not explicitly permitted is denied (BACKEND_ARCHITECTURE.md §22).

### 6.7 Exception Handling

- Centralized exception handling produces the uniform error envelope (error code, message, details) for every error type (BACKEND_ARCHITECTURE.md §15; API_SPECIFICATION.md §8).
- Correct HTTP status codes per error class (400/401/403/404/409/422/500) (PROJECT_RULES.md API Standards).
- Stack traces never reach the client; full details go to server logs only (PROJECT_RULES.md Error Handling Standards).
- Retry/fallback behavior for transient failures verified (BACKEND_ARCHITECTURE.md §24).

---

## 7. Database Testing

Database testing validates the schema and behavior defined in **DATABASE_DESIGN.md** — the single source of truth for all persistence work. Tests run against a dedicated test database (PostgreSQL in CI-equivalent environments; SQLite only for local-fast unit runs) — never the production database (BACKEND_ARCHITECTURE.md §26).

### 7.1 CRUD Operations

- Create, read, update, and delete verified for all 16 tables (DATABASE_DESIGN.md §12–25).
- Soft delete behavior verified: `deleted_at` set, rows hidden from normal queries, restore works (DATABASE_DESIGN.md §26).
- Append-only tables (`audit_logs`, `agent_logs`, `request_timeline`) accept writes and never update/delete in normal operation (DATABASE_DESIGN.md §34.4).

### 7.2 Relationships

- Foreign-key relationships verified for correctness and direction (DATABASE_DESIGN.md §8, §11).
- Cascade/restrict behaviors verified per DATABASE_DESIGN.md §27 — orphan prevention, no accidental mass deletes.
- 1:1 relationships (e.g., `users` ↔ `students`) enforced; required related rows are created atomically.

### 7.3 Constraints

- `NOT NULL`, `UNIQUE`, `CHECK`, enum, and foreign-key constraints reject invalid data (DATABASE_DESIGN.md §10).
- Constraint violations surface as typed, friendly errors — never raw driver exceptions (BACKEND_ARCHITECTURE.md §15).
- Partial unique constraints (e.g., deduplicated citations) verified (DATABASE_DESIGN.md §22.2).

### 7.4 Transactions

- ACID behavior verified: atomicity (all-or-nothing), commit-once, automatic rollback on failure (DATABASE_DESIGN.md §34).
- Write + audit in one commit; append-only rows never recorded for rolled-back work (DATABASE_DESIGN.md §34.3–34.4).
- Optimistic concurrency: version mismatch yields `409 Conflict`; retry on fresh data works (DATABASE_DESIGN.md §34.5).
- Row-locking and fixed-lock-order behavior verified for high-contention paths; deadlock retry with bounded backoff verified (DATABASE_DESIGN.md §34.6–34.8).
- Background jobs commit per-unit, never across a whole job (DATABASE_DESIGN.md §34.2).

### 7.5 Migrations

- Alembic migrations apply cleanly on an empty database and upgrade existing databases without data loss (DATABASE_DESIGN.md §28).
- Downgrades are tested for reversible migrations; data migrations verified with representative data.
- Migration history matches the documented schema; no drift between models and migrations.

### 7.6 Index Validation

- Every index defined in DATABASE_DESIGN.md §9 exists and is used by the queries it serves.
- Unique indexes enforce uniqueness; composite indexes support the documented keyset pagination and filters.
- Missing or redundant indexes detected via query-plan inspection during performance tests (Section 16).

### 7.7 Performance

- Query performance validated against DATABASE_DESIGN.md §31 targets: no full-table scans on hot paths, bounded pagination, efficient counts.
- Concurrency and lock behavior under load validated (Section 16.2).
- Retention/purge jobs (DATABASE_DESIGN.md §35) run within time budgets on representative data volumes.

---

## 8. API Testing

API testing verifies the complete contract defined in **API_SPECIFICATION.md** — the single source of truth for all endpoints. Every endpoint in Sections 15–24 is covered by contract-level tests. Testing follows the API Testing Strategy (API_SPECIFICATION.md §38).

### 8.1 Request Validation

- Every request schema validated: required fields, types, formats, lengths, enums (Pydantic v2, API_SPECIFICATION.md §12).
- Invalid payloads return `422` with the standard validation error shape.
- Unknown fields, duplicate fields, and malformed JSON handled per spec.

### 8.2 Response Validation

- Every response matches its documented schema (API_SPECIFICATION.md §7) — field names, types, nesting, and nullability.
- Response envelopes are consistent: data, pagination metadata, error shapes.
- OpenAPI-generated docs match the implemented behavior (API_SPECIFICATION.md §30, §38 — Swagger verification).

### 8.3 Status Codes

- Correct status code per operation (200/201/204/400/401/403/404/409/422/500) per API_SPECIFICATION.md §27.
- Created resources return their location/identifier as specified.
- No operation returns an undocumented status code.

### 8.4 Error Responses

- Every error uses the uniform envelope (error code, message, details) per API_SPECIFICATION.md §8 and §26.
- Each documented error code (AUTH/USER/REQ/CHAT/AI/KB/SYS/VAL) is tested with a triggering scenario.
- Client never receives stack traces or internal identifiers.

### 8.5 Pagination

- Page/offset contract works per API_SPECIFICATION.md §9; keyset pagination behavior verified on large collections.
- Defaults, limits, overflow behavior, and metadata (`total`, `page`, `page_size`, `has_more`) verified.
- Pagination is stable under concurrent inserts (no skipped/duplicated rows).

### 8.6 Filtering

- Whitelisted, indexed filter fields behave per API_SPECIFICATION.md §10.
- Invalid/unknown filter fields are rejected per spec.
- Combined filters compose correctly (e.g., status + category).

### 8.7 Sorting

- Only whitelisted, indexed sort fields accepted (API_SPECIFICATION.md §11; DATABASE_DESIGN.md §31).
- Ascending/descending verified; default sort order stable and documented.
- Unknown sort fields rejected.

### 8.8 Authentication

- Protected endpoints reject missing/invalid/expired tokens with `401`.
- Role-restricted endpoints reject unauthorized roles with `403` (API_SPECIFICATION.md §4).
- Idempotency keys honored on write endpoints (API_SPECIFICATION.md §34).
- Rate limiting (API_SPECIFICATION.md §13) returns the specified `429` behavior.

---

## 9. Authentication Testing

Authentication testing verifies the complete identity lifecycle defined in **API_SPECIFICATION.md** (§3–5), **BACKEND_ARCHITECTURE.md** (§9), and **DATABASE_DESIGN.md** (§25).

### 9.1 Login

- Valid credentials produce access + refresh tokens; invalid credentials return the standard `401` error shape (no user enumeration).
- Login with locked/deactivated accounts is rejected.
- Rate-limited repeated failures return `429` (API_SPECIFICATION.md §13).
- Sessions are recorded server-side and rotation-safe (DATABASE_DESIGN.md §25).

### 9.2 Register

- Registration validates all fields client-side and server-side; duplicate emails rejected (DATABASE_DESIGN.md §12).
- Password policy enforced (strength/length) on both sides.
- Successful registration creates the `users` record and initiates email verification (Section 9.8).

### 9.3 JWT

- Access tokens are signed with `JWT_SECRET`, expire per policy, and carry only the documented claims (API_SPECIFICATION.md §5).
- Tampered tokens are rejected; tokens signed with the wrong secret are rejected.
- Refresh tokens are long-lived, server-side records, stored hashed (DATABASE_DESIGN.md §25).
- Refresh rotation: a rotated refresh token is invalidated; replay is detected (DATABASE_DESIGN.md §25).

### 9.4 Token Expiration

- Expired access tokens return `401` and a refresh path works.
- Expired/revoked refresh tokens force re-login with the correct flow.
- Expiry behavior verified with controlled, fast-marching test clocks — no waiting on real time.

### 9.5 Protected Routes

- Every protected frontend route redirects to Login; protected API endpoints reject unauthenticated calls.
- No protected data is server-rendered or client-cached without a valid session.

### 9.6 Authorization

- RBAC matrix tested exhaustively: student, admin, and (future) AI-operator roles per API_SPECIFICATION.md §4.
- Owner-scope violations rejected (user A cannot access user B's requests/conversations/notifications) (DATABASE_DESIGN.md §30).
- Admin-only endpoints reject students with `403`.

### 9.7 Password Reset

- Reset request flow: email issued, token single-use, expiry enforced, rate-limited.
- Reset with invalid/expired/reused tokens rejected.
- Password reset invalidates existing sessions/tokens per design.

### 9.8 Email Verification

- Verification token issued at registration; valid token confirms the account; invalid/expired tokens rejected.
- Verified/unverified status drives the documented restrictions.
- Email dispatch is mocked in automated tests; delivery verified in smoke/integration environments.

---

## 10. AI Testing

AI testing verifies the AI system against the standards and metrics defined in **AI_ARCHITECTURE.md** — the single source of truth for all AI decisions. The evaluation framework (AI_ARCHITECTURE.md §38) defines the metrics that AI tests must protect.

### 10.1 Prompt Quality

- Every agent owns a versioned prompt stored in `ai/prompts/` (PROJECT_RULES.md Prompt Engineering Rules).
- Prompts tested for consistency, modularity, and correct injection of dynamic variables (AI_ARCHITECTURE.md §13, §34).
- Prompt changes are regression-tested via the evaluation harness (AI_ARCHITECTURE.md §38.3).
- Structured-output prompts produce the documented schemas reliably.

### 10.2 Response Quality

- Response accuracy evaluated on a curated, versioned evaluation set (AI_ARCHITECTURE.md §38.1).
- Response formatting verified against ui-ux-design.md §14 and AI_ARCHITECTURE.md §27: short paragraphs, bullets, numbered steps, tables only where appropriate, no walls of text.
- Professional tone and student-first language verified per PROJECT_RULES.md AI Behaviour Rules.

### 10.3 Agent Routing

- Coordinator routing accuracy: the correct specialist (Admission / Examination / FAQ) is chosen for the true intent (AI_ARCHITECTURE.md §9, §38.1).
- Ambiguous intents trigger the clarify path (confidence below threshold) (AI_ARCHITECTURE.md §9.5, §11.3).
- Out-of-scope intents are handled with the scope boundary + referral — never misrouted (AI_ARCHITECTURE.md §25).

### 10.4 Hallucination Detection

- Hallucination rate is measured on the evaluation harness and kept near zero (AI_ARCHITECTURE.md §20, §38.1).
- Unsupported claims are caught by the post-processing grounding check (AI_ARCHITECTURE.md §18.4).
- No-answer policy verified: the assistant never answers without evidence (AI_ARCHITECTURE.md §28.3).

### 10.5 Citation Validation

- Citation accuracy: every citation genuinely supports the claim it accompanies (AI_ARCHITECTURE.md §19, §38.1).
- Sources are tracked per message in `ai_sources` (DATABASE_DESIGN.md §22).
- Duplicate chunk citations are deduplicated (DATABASE_DESIGN.md §22.2); missing citations on grounded claims are flagged.

### 10.6 Context Accuracy

- Retrieved context is relevant, deduplicated, and correctly prioritized (AI_ARCHITECTURE.md §17).
- Token budget respected; history + retrieval never silently truncated (AI_ARCHITECTURE.md §17.3, §21.6).
- Only active, processed, current-version documents contribute to context (AI_ARCHITECTURE.md §16.4).

### 10.7 Response Formatting

- Output passes the formatting rules (AI_ARCHITECTURE.md §27) and is safe to render (no raw HTML) (AI_ARCHITECTURE.md §26.4).
- Markdown preserved correctly for headings, lists, tables, links, code.
- Long responses support Copy; sources are collapsible (ui-ux-design.md §31).

### 10.8 Confidence Handling

- Low-confidence answers are never presented as definitive; clarify/partial/no-answer behaviors verified (AI_ARCHITECTURE.md §28).
- Retrieval-score thresholds, intent confidence thresholds, and answer-validation results drive the correct fallback matrix (AI_ARCHITECTURE.md §28.4).

---

## 11. LangGraph Testing

LangGraph testing verifies the agent workflow defined in **AI_ARCHITECTURE.md** §11–12 — the state machine that coordinates the Coordinator and specialist agents.

### 11.1 Graph Execution

- The graph compiles and executes end to end: entry → Detect Intent → Route → Specialist → Build Context → Generate → Assemble Citations → Aggregate → Persist → exit (AI_ARCHITECTURE.md §11.2).
- Full, happy-path runs produce the documented Coordinator envelope: answer, citations, handoff, status.
- Timeout and cancellation of a run behave correctly (AI_ARCHITECTURE.md §23).

### 11.2 Node Execution

- Each node tested in isolation (Detect Intent, Route, Retrieve, Build Context, Generate, Assemble Citations, Aggregate, Persist) per AI_ARCHITECTURE.md §11.2.
- Node inputs/outputs conform to the typed state schema; node failures raise typed errors.
- Persist node writes messages, sources, and logs correctly and updates counters (DATABASE_DESIGN.md §15–16, §24).

### 11.3 State Management

- Conversation state flows correctly through the graph per the state model (AI_ARCHITECTURE.md §12).
- State is rebuilt from persisted data at session start; the AI service never relies on in-process state (AI_ARCHITECTURE.md §21.4).
- State transitions match the documented edges (AI_ARCHITECTURE.md §11.3).

### 11.4 Routing

- Router edges select the correct specialist; clarify-loop edges trigger below confidence threshold (AI_ARCHITECTURE.md §11.3).
- Every routing decision is logged to `agent_logs` (AI_ARCHITECTURE.md §11.2, §30.1).
- Routing is deterministic for a fixed intent signal (tested with fixed inputs).

### 11.5 Error Recovery

- Node failure → typed error → friendly response + retry option, per the error-recovery matrix (AI_ARCHITECTURE.md §23.1).
- Transient failures retried with bounded backoff; idempotent operations only (BACKEND_ARCHITECTURE.md §24).
- Graph-level failure never leaves partial, inconsistent persistence (transactional Persist node).

### 11.6 Agent Handoff

- Handoff between agents (when applicable) preserves context and is logged (AI_ARCHITECTURE.md §24; DATABASE_DESIGN.md §24).
- Handoff UX surfaces the agent identity chip per ui-ux-design.md.
- No-answer and referral transitions hand off to the correct department recommendation.

---

## 12. RAG Testing

RAG testing verifies the retrieval pipeline defined in **AI_ARCHITECTURE.md** §14–19 against the knowledge-base and vector-store design (DATABASE_DESIGN.md §20–22).

### 12.1 Document Retrieval

- The retriever returns relevant chunks for representative queries per category (admission, examination, faq, documents) (AI_ARCHITECTURE.md §16).
- Retrieval accuracy is measured on a ground-truth retrieval set per AI_ARCHITECTURE.md §38.1.
- Metadata filters applied: category scope, `is_active = true`, `status = 'processed'`, current version only (AI_ARCHITECTURE.md §16.4).

### 12.2 Embedding Accuracy

- The query and corpus share the same embedding model (Sentence Transformers) and distance metric (AI_ARCHITECTURE.md §16.1–16.2).
- Embedding drift on model change is detected by a golden retrieval set — re-embedding is required when the model changes.
- Embedding dimension/format consistency verified at index build and query time.

### 12.3 Chunk Retrieval

- `RAG_TOP_K` (default 4) chunks returned per query; configurable per agent (AI_ARCHITECTURE.md §16.5).
- Top-K relevance verified against ground truth; irrelevant chunks flagged for chunking/embedding fixes.
- Chunk-level filters (heading, page, section metadata) behave per DATABASE_DESIGN.md §21.2.

### 12.4 Context Building

- Retrieved chunks are assembled within the token budget; deduplicated and prioritized (AI_ARCHITECTURE.md §17).
- History + retrieval + system rules combined in the correct order within budget (AI_ARCHITECTURE.md §17.3).
- No context loss: token limits handled by trimming/priority, never silent truncation.

### 12.5 Citation Accuracy

- Every generated citation maps to a real retrieved chunk with source metadata (title, url/path, category, snippet, relevance) (AI_ARCHITECTURE.md §19; API_SPECIFICATION.md §21).
- Citation de-duplication verified (one citation per chunk per message) (DATABASE_DESIGN.md §22.2).
- A hallucinated citation (source does not support the claim) fails the test.

### 12.6 Knowledge Coverage

- Coverage measured across categories and intents: can the system answer the expected university queries? (AI_ARCHITECTURE.md §38.1 — Retrieval Accuracy per category).
- Knowledge gaps surface as "information unavailable" + referral — verified correct, never invented.
- Coverage improvements are tracked over eval cycles (AI_ARCHITECTURE.md §38.3).

---

## 13. Knowledge Base Testing

Knowledge base testing verifies document and knowledge management per **AI_ARCHITECTURE.md** §36 and **DATABASE_DESIGN.md** §20–21.

### 13.1 Document Upload

- Uploads validate type, size, and checksum (SHA-256) per API_SPECIFICATION.md §35 and DATABASE_DESIGN.md §20.
- Duplicate uploads detected; versioning applied instead of duplication (AI_ARCHITECTURE.md §36).
- Upload status lifecycle (pending → processing → processed/failed) tracked in `documents`/`knowledge_documents`.

### 13.2 Chunking

- Chunking produces consistent, retrievable chunks with source metadata (AI_ARCHITECTURE.md §14.3, §36).
- Chunk boundaries don't corrupt meaning (no split mid-sentence where avoidable); chunk sizes within configured bounds.
- Chunk regeneration is idempotent — re-running ingestion produces equivalent chunks without orphan data.

### 13.3 Metadata

- Every chunk carries heading, page, section, source, and category metadata (DATABASE_DESIGN.md §21.2).
- Metadata filtering works end to end (Section 12.1).
- Malformed/missing metadata fails ingestion with a typed error.

### 13.4 Versioning

- Document versions managed: superseded versions soft-deleted and archived; 2 superseded versions retained (AI_ARCHITECTURE.md §36; DATABASE_DESIGN.md §35).
- Only the current active version is retrievable (AI_ARCHITECTURE.md §16.4).
- Version history preserved and auditable.

### 13.5 Re-indexing

- Re-indexing regenerates the FAISS index from source documents (BACKEND_ARCHITECTURE.md §21; DATABASE_DESIGN.md §21).
- Re-index is idempotent and runs as a background job, never on the request path (BACKEND_ARCHITECTURE.md §19; API_SPECIFICATION.md §36.2).
- Index regeneration is verified against a golden retrieval set before swap.
- Missing/corrupt index detected by health checks and recovered (AI_ARCHITECTURE.md §31.1).

### 13.6 Retrieval Quality

- Retrieval quality regression-tested after every ingestion, chunking, or embedding change.
- Category-level retrieval accuracy tracked (admission/examination/faq/documents) per AI_ARCHITECTURE.md §38.1.
- Knowledge coverage reports drive content additions (Section 12.6).

---

## 14. Conversation Testing

Conversation testing verifies the chat experience end to end per **ui-ux-design.md** §13 and §36, **AI_ARCHITECTURE.md** §21–22, and **API_SPECIFICATION.md** §20–22.

### 14.1 Chat Sessions

- Session lifecycle verified: created on first message, active turns, idle/expiry, archived, restored (AI_ARCHITECTURE.md §22; DATABASE_DESIGN.md §15, §25).
- A new chat creates a fresh conversation; the conversation sidebar reflects state accurately.
- Auth session and AI conversation are correctly separated (AI_ARCHITECTURE.md §22.2).

### 14.2 Conversation Memory

- Short-term memory window (default 20 turns) preserved and injected (AI_ARCHITECTURE.md §21.2).
- Follow-up questions resolve correctly using prior turns.
- Long-term memory (opt-in) summarizes and reconstructs context on restore (AI_ARCHITECTURE.md §21.3).

### 14.3 Streaming Responses

- Responses stream token-by-token — never a single delayed block (ui-ux-design.md §31.1).
- Streaming states (thinking/loading, partial tokens, completed) render correctly (ui-ux-design.md §36).
- `aria-live` announces streaming/updates for screen readers (ui-ux-design.md §41).
- Streaming interruption (stop/refresh/network) handled gracefully; partial content handled or discarded per spec.

### 14.4 History

- Every message persisted in `chat_history` at the Persist node (AI_ARCHITECTURE.md §21.5; DATABASE_DESIGN.md §16).
- Chat history page lists conversations with correct metadata (message count, tokens, timestamps).
- History is owner-scoped: users see only their own conversations (DATABASE_DESIGN.md §30).

### 14.5 Resume Conversations

- Archived conversations can be restored; restored context (summary + recent window) reconstructs the conversation (AI_ARCHITECTURE.md §22.5, §21.3).
- Resuming a conversation routes correctly and does not corrupt memory state.
- Delete conversation removes per the documented lifecycle; audit trail intact (DATABASE_DESIGN.md §35).

### 14.6 Session Expiration

- Expired auth sessions require re-login; the draft message is preserved and re-sent after login (ui-ux-design.md §36).
- Idle conversations reach the documented expiry and archive state.
- Session rotation/replay detection verified (DATABASE_DESIGN.md §25).

---

## 15. Security Testing

Security testing validates the security architecture defined in **BACKEND_ARCHITECTURE.md** §22, **API_SPECIFICATION.md** §28, **DATABASE_DESIGN.md** §30, and the AI guardrails in **AI_ARCHITECTURE.md** §26. Security is validated by automated tests, manual review, and a scheduled manual security pass.

### 15.1 Authentication

- Brute-force/rate-limit protections verified (API_SPECIFICATION.md §13).
- Credential stuffing, user enumeration, and timing-difference probes considered.
- Session fixation, token theft (stolen refresh token), and replay scenarios tested.

### 15.2 Authorization

- RBAC matrix exhaustively tested (Section 9.6).
- Horizontal (owner-scope) and vertical (role) privilege-escalation attempts rejected.
- IDOR (insecure direct object reference) probes: user A cannot read/update user B's resources.

### 15.3 SQL Injection

- All queries use parameterized ORM queries — never string-built SQL (BACKEND_ARCHITECTURE.md §22; DATABASE_DESIGN.md §30).
- Injection payloads in fields, filters, and sort parameters are neutralized and tested.

### 15.4 XSS

- Output escaped/sanitized; no unsafe HTML from user content (BACKEND_ARCHITECTURE.md §22).
- AI response Markdown rendering sanitized client-side — no raw HTML (AI_ARCHITECTURE.md §26.4).
- Stored, reflected, and DOM XSS vectors tested on user-supplied fields and AI output.

### 15.5 CSRF

- State-changing requests protected per API_SPECIFICATION.md §28 (token/same-site policy as designed).
- Cross-site request forgery attempts rejected.

### 15.6 Prompt Injection

- User content treated as data, never instructions; delimited, non-executable injection (AI_ARCHITECTURE.md §26.1).
- Jailbreak/role-play/authority-invocation attempts detected and safely refused (AI_ARCHITECTURE.md §26.2).
- Guardrail checks on both input and output verified; blocked output replaced with safe fallback and logged (AI_ARCHITECTURE.md §26.4–26.5).

### 15.7 Data Leakage

- Cross-account data leakage tested (conversations, requests, notifications, documents).
- Audit and agent logs contain no secrets, tokens, passwords, or raw PII (AI_ARCHITECTURE.md §30.2).
- Error responses never leak internal details; stack traces server-only.

### 15.8 PII Protection

- PII minimized, redacted in logs (user references use ids) (AI_ARCHITECTURE.md §30.2, §37).
- Student data never shared across accounts; confidentiality enforced (AI_ARCHITECTURE.md §25.1).
- Retention and consent respected per DATABASE_DESIGN.md §35 (research corpus consent, anonymization).

---

## 16. Performance Testing

Performance testing validates the performance budgets in **API_SPECIFICATION.md** §36, **AI_ARCHITECTURE.md** §31–32, and **DATABASE_DESIGN.md** §31. The `testing/load/` folder hosts load and stress assets.

### 16.1 API Response Time

- Read/list endpoints sub-second at p95; write endpoints sub-second; health checks sub-second (API_SPECIFICATION.md §36.1).
- AI endpoints bounded by model latency with TTFT optimized (AI_ARCHITECTURE.md §31.2).
- Percentiles (p50/p95/p99) tracked and compared against budgets in every perf cycle.

### 16.2 Database Performance

- Query plans inspected for hot endpoints; indexes validated (Section 7.6).
- Pagination efficiency on large collections (keyset, no full scans) (DATABASE_DESIGN.md §31).
- Concurrency behavior under parallel writes verified (locking, optimistic conflicts at expected rates).

### 16.3 AI Response Time

- End-to-end response time, node latencies (detection, retrieval, generation), and streaming TTFT tracked (AI_ARCHITECTURE.md §31.2).
- Token usage per message/conversation/agent/model measured (AI_ARCHITECTURE.md §31.3).
- Degradation beyond budgets triggers the fallback/alerting path (AI_ARCHITECTURE.md §31.5).

### 16.4 Concurrent Users

- Realistic concurrency profiles (students, admin) simulated against the stack.
- Behavior verified at expected, peak, and above-peak concurrency; errors stay within acceptable bounds.

### 16.5 Load Testing

- Sustained load runs verify throughput, latency stability, and resource utilization (CPU/memory/db connections).
- FAISS in-memory index behavior under concurrent retrieval measured.
- Background jobs (indexing, notifications, retention) do not destabilize the API under load.

### 16.6 Stress Testing

- Load beyond designed capacity: graceful degradation, no crashes, recovery after load is removed.
- Database connection pool exhaustion behavior verified (bounded, typed errors, recovery) (BACKEND_ARCHITECTURE.md §23).

### 16.7 Scalability

- Stateless API nodes verified: horizontal scaling does not break sessions/state (state lives in DB) (BACKEND_ARCHITECTURE.md §23; API_SPECIFICATION.md §3).
- Vector store and memory scale per AI_ARCHITECTURE.md §32 (index in memory, metadata filtering, top-K tuning).

---

## 17. UI/UX Testing

UI/UX testing verifies the interface against **ui-ux-design.md** (its single source of truth). It is primarily manual + assistive-technology testing, supported by automated component/accessibility checks.

### 17.1 Responsive Design

- Layouts verified at all breakpoints (ui-ux-design.md §8); no horizontal overflow (ui-ux-design.md §41).
- Mobile, tablet, and desktop behaviors match the layout guidelines (ui-ux-design.md §7, §37).

### 17.2 Accessibility

- WCAG AA contrast, reduced-motion support (ui-ux-design.md §22).
- Accessible names, roles, and states on all interactive elements.

### 17.3 Keyboard Navigation

- Full tab order; arrow keys in menus/tabs; Esc closes overlays; focus never lost (ui-ux-design.md §41).
- Visible 2px focus ring + 4px offset (ui-ux-design.md §22).

### 17.4 Screen Readers

- Semantic HTML; `aria-live` for chat/streaming/toasts; alt text; one `h1` per page (ui-ux-design.md §41).
- Screen-reader passes with at least one major reader (e.g., NVDA/VoiceOver) on critical flows (login, chat, dashboard).

### 17.5 Mobile Experience

- ≥44px touch targets; sticky chat input; safe areas; drawer navigation; pull-to-refresh (ui-ux-design.md §37, §41).
- Mobile chat UX verified per the mobile guidelines (ui-ux-design.md §37).

### 17.6 Empty States

- Every list/dashboard has a meaningful empty state per ui-ux-design.md §34.
- Empty states guide the user to the next action (e.g., "Start a chat", "No requests yet").

### 17.7 Loading States

- Spinner/skeleton on every async view; no blank screens (ui-ux-design.md §41).
- Skeletons match final layout; no layout shift (CLS-safe).

### 17.8 Error States

- Friendly message + Retry on every failure; drafts preserved; no stack traces (ui-ux-design.md §35, §41).
- Offline/disconnected state handled gracefully.

---

## 18. Browser Compatibility Testing

The supported browsers are **Chrome, Edge, Firefox, and Safari** (current stable versions). Compatibility is verified on the E2E and staging environments.

| Browser | Coverage |
| ------- | -------- |
| **Chrome** | Primary development target; full automated E2E suite + manual UX pass. |
| **Edge** | Same engine family as Chrome; automated E2E subset + manual pass on key flows. |
| **Firefox** | Automated E2E subset + manual pass; verify rendering, focus, and screen-reader behavior. |
| **Safari** | Manual pass on key flows (automation where available); verify WebKit rendering, `aria-live`, and streaming behavior. |

**Rules:**
- Critical flows (login, chat, request workflow) verified on all four browsers for each release candidate.
- Feature-flagged or experimental Web APIs are avoided or polyfilled consistently.
- Browser differences in form behavior, focus, and animation are captured in the manual test checklist.

---

## 19. Device Testing

Device testing verifies responsive behavior across the device classes defined in **ui-ux-design.md** §8 and §37. It is primarily manual and performed on the staging environment.

| Device class | Viewport/behaviors verified |
| ------------ | --------------------------- |
| **Mobile** | ≤ mobile breakpoint: drawer navigation, sticky chat input, 44px targets, safe areas, card-ized tables. |
| **Tablet** | Tablet breakpoint: rail sidebar, 2-column grids, readable tables. |
| **Laptop** | Laptop breakpoints: standard dashboard layout, full sidebar, tables readable. |
| **Desktop** | Desktop breakpoints: full sidebar, 4-column stats, content ≤1280px (ui-ux-design.md §7). |

**Rules:**
- No device class is an afterthought — each is verified at every release.
- Real-device passes supplement browser-device-mode checks for touch, safe areas, and performance.
- Findings are logged in the device matrix and fixed before release.

---

## 20. Regression Testing

Regression testing protects the system against unintended behavior changes. It is a continuous, automated activity driven by the architecture docs.

### 20.1 Regression Policy

| Rule | Detail |
| ----- | ------ |
| **Every fix is protected** | Any defect fixed is covered by a regression test that fails if it recurs. |
| **Every merge is protected** | The full fast suite runs on every feature-branch merge (Section 28.5). |
| **AI regressions gated** | Prompt/retrieval/model/KB changes must not regress evaluation metrics (AI_ARCHITECTURE.md §38.3). |
| **No silent drift** | Endpoint contracts, UI behavior, and database behavior are pinned by tests; deviations fail CI. |
| **Scope by change** | Small changes run fast targeted suites; releases run the full regression suite. |

### 20.2 Test Coverage

- Regression coverage includes: unit, integration, API contract, E2E critical journeys, RAG golden sets, and AI evaluation harness.
- Coverage is maintained at the standards in Section 29 — regression protection is only as good as coverage.
- New features add their regression tests at the same time as the feature (Definition of Done).

### 20.3 Automation Strategy

- Regression is fully automated and runs in CI on every push/merge (Section 28.5).
- Flaky regression tests are treated as defects: quarantined, fixed, and returned within the cycle (Section 1.5).
- Regression results feed the quality gates (Section 31) — a regression failure blocks the release.

---

## 21. Smoke Testing

Smoke testing is the fast, shallow verification that the system's most critical paths work after a build or deployment. It runs on every build candidate and after every deployment.

### 21.1 Critical Features

| Feature | Smoke check |
| ------- | ----------- |
| Health check | `/api/v1/health` returns healthy (API_SPECIFICATION.md §24). |
| Login/Register | Auth endpoints respond; a known user can obtain tokens. |
| Chat | A minimal chat round-trip completes and persists a message. |
| RAG | A canonical knowledge query returns a grounded response with citations. |
| Request workflow | A request can be created and tracked through its first status. |
| Frontend boot | Key pages render without runtime errors. |

### 21.2 Build Verification

- Smoke runs on every CI build candidate before longer suites execute.
- A failed smoke aborts the build pipeline immediately — no further testing on a broken build.
- Smoke checks assert only stability, never deep correctness (deep checks live in system/E2E suites).

### 21.3 Deployment Validation

- Post-deployment smoke validates the *deployed* environment (staging/production candidate) — health, DB reachable, vector store reachable, LLM gateway reachable (AI_ARCHITECTURE.md §31.1).
- Deployment smoke catches configuration/environment drift that unit tests cannot (Section 27.4).
- Any smoke failure on staging blocks promotion to production.

---

## 22. User Acceptance Testing (UAT)

UAT confirms the system is fit for real use by SMIU students and satisfies the FYP requirements. It is the final, user-facing acceptance gate.

### 22.1 Acceptance Criteria

- Every feature has documented, testable acceptance criteria derived from the requirements (PROJECT_RULES.md Phase 1 scope) and the architecture docs.
- Acceptance criteria are reviewed with the FYP supervisor before UAT begins.
- A feature is accepted only when all its criteria are met and evidence is recorded.

### 22.2 Student Testing

- Representative SMIU students test the real system (staging) against real scenarios: admission queries, examination queries, FAQs, request tracking.
- Structured UAT scripts cover critical journeys; exploratory testing captures unexpected findings.
- Students test on real devices and browsers (Sections 18–19).

### 22.3 Feedback Collection

- Feedback captured via the `feedback` mechanism (ratings/comments/flags — DATABASE_DESIGN.md §23) and a UAT feedback form.
- Feedback is triaged: defects vs. improvements vs. out-of-scope (AI_ARCHITECTURE.md §29).
- AI-specific feedback feeds the evaluation loop (AI_ARCHITECTURE.md §29.3).

### 22.4 Final Approval

- UAT results, defect status, and feedback resolutions are summarized (Section 32).
- Final approval is recorded with the supervisor's sign-off against the acceptance criteria.
- Approved = release candidate; unresolved blocking defects prevent approval (Section 31).

---

## 23. Test Data Management

Test data management ensures every test is deterministic, isolated, and reproducible (Section 1.7). It follows the seeding and cleanup design in the project (PROJECT_RULES.md — database seeds).

### 23.1 Sample Data

- Versioned sample data reflects the real university domain: departments, admission guides, examination policies, FAQs (knowledge base) (PROJECT_RULES.md Knowledge Base Structure).
- Sample data lives with the repo so environments can reproduce it (Section 27).
- Sample data is realistic but contains no real PII (Section 15.8).

### 23.2 Mock Data

- Mocked external boundaries: LLM (Gemini 2.5 Flash), email dispatch, and network services are simulated deterministically in automated tests (BACKEND_ARCHITECTURE.md §26).
- Mocked LLM responses are curated to exercise happy, edge, and failure paths (Section 24).
- Factories generate isolated per-test entities without shared-state collisions.

### 23.3 AI Test Prompts

- A **versioned golden prompt set** covers every agent, intent, edge case, and restricted topic (Section 10).
- Prompt fixtures include: typical queries, ambiguous queries, out-of-scope queries, injection attempts, jailbreak attempts.
- The golden set drives the evaluation harness and AI regression runs (AI_ARCHITECTURE.md §38.3).

### 23.4 Database Seeding

- Seeding follows the documented seed strategy (PROJECT_RULES.md; DATABASE_DESIGN.md §28).
- Each test tier seeds the minimum data it needs; integration/system/E2E use dedicated seed profiles.
- Seeds are idempotent and versioned; schema changes invalidate old seed versions.

### 23.5 Cleanup Strategy

- Tests clean up their own data (transaction rollback or test-DB reset) — no leakage between runs (Section 1.7).
- E2E and integration databases are reset to a pristine seed state before each suite.
- Knowledge-base index artifacts are regenerated, never shared between test runs.

---

## 24. Error Testing

Error testing verifies that failures are handled gracefully, typed, and recoverable per **BACKEND_ARCHITECTURE.md** §24, **API_SPECIFICATION.md** §8 and §26, and **AI_ARCHITECTURE.md** §23.

### 24.1 Invalid Input

- Malformed, missing, out-of-range, and type-wrong inputs return the standard validation error shape (`422`/`400`) (API_SPECIFICATION.md §12).
- Validation is verified at both client and server boundaries.

### 24.2 Server Errors

- Simulated internal failures return `500` with the standard envelope — never stack traces.
- Centralized exception handling applies consistently across routes and services (BACKEND_ARCHITECTURE.md §15).
- Error responses are logged server-side with correlation IDs (Section 25).

### 24.3 Network Failures

- Downstream network loss (LLM gateway, third-party) triggers typed errors and the documented retry/fallback path (BACKEND_ARCHITECTURE.md §24).
- Retries are bounded with backoff; only idempotent operations are retried.
- Client sees a friendly error + retry; drafts preserved (ui-ux-design.md §35–36).

### 24.4 Database Failures

- Connection loss, timeout, and constraint races handled without partial commits (DATABASE_DESIGN.md §34.4).
- Connection-pool exhaustion produces bounded, typed errors and recovery.
- Background jobs retry failed units without corrupting state (DATABASE_DESIGN.md §34.2).

### 24.5 AI Failures

- LLM timeout, malformed output, guardrail block, and retrieval failure each map to a typed error and friendly behavior (AI_ARCHITECTURE.md §23).
- Fallback matrix verified: clarify → retrieve narrower → no-answer with referral (AI_ARCHITECTURE.md §23.1, §28.4).
- No-answer responses are clear, professional, and refer to the correct department (PROJECT_RULES.md AI Behaviour Rules).

---

## 25. Logging & Debugging

Logging supports observability and debugging per **PROJECT_RULES.md** (Logging & Monitoring), **BACKEND_ARCHITECTURE.md** §16, **AI_ARCHITECTURE.md** §30, and **API_SPECIFICATION.md** §37. Testing verifies that logging is correct, complete, and safe.

### 25.1 Error Logs

- Every error/exception logged with level, message, error code, correlation ID, and timestamp.
- Logs include enough detail to debug, but never secrets, tokens, or raw PII (PROJECT_RULES.md).
- Log-level behavior (DEBUG/INFO/WARNING/ERROR/CRITICAL) verified in test and production configs.

### 25.2 API Logs

- Request logging: method, path, status, duration, user id (when available) (API_SPECIFICATION.md §37).
- Response logging: response size, status, latency bucket.
- Correlation ID (`X-Correlation-Id`) propagated across backend → AI → DB (API_SPECIFICATION.md §37; AI_ARCHITECTURE.md §30.2).

### 25.3 AI Logs

- AI logs capture model, tokens, latency, routing decisions, retrieval runs/scores/chunk ids, and structured outputs (AI_ARCHITECTURE.md §30.1).
- Guardrail blocks, injection attempts, and safety events logged to `audit_logs` (AI_ARCHITECTURE.md §30.1, §26.5).
- Grounding traces recorded in `agent_logs` for auditability (AI_ARCHITECTURE.md §30.1).

### 25.4 Audit Logs

- Privileged/sensitive actions recorded in `audit_logs` per DATABASE_DESIGN.md §24.
- Audit rows are written in the same transaction as the change; append-only (DATABASE_DESIGN.md §34.3–34.4).
- Audit retention (7 years+) per DATABASE_DESIGN.md §35.

### 25.5 Debug Strategy

- Debugging uses correlation IDs to trace a request across all services.
- Debug builds/logs are controlled by configuration — never hardcoded.
- Reproducing a defect uses the deterministic test data and seed strategy (Section 23).
- Logs from the AI evaluation harness (retrieval scores, routing signals) are first-class debugging assets (AI_ARCHITECTURE.md §38.2).

---

## 26. Monitoring

Monitoring extends testing into production-like operation, validating the monitoring design in **AI_ARCHITECTURE.md** §31 and **API_SPECIFICATION.md** §37. Test environments themselves are monitored so issues surface early.

### 26.1 Health Monitoring

- Health endpoint reports API, database, vector store, and LLM gateway status (API_SPECIFICATION.md §24; AI_ARCHITECTURE.md §31.1).
- Degraded states surfaced to operators and produce fallback behavior (AI_ARCHITECTURE.md §31.1).
- Health checks validated automatically in smoke and system tests (Section 21).

### 26.2 Error Monitoring

- Error rate, retry rate, fallback rate, and timeout rate tracked per node and per agent (AI_ARCHITECTURE.md §31.5).
- Alerting thresholds on sustained degradation validated with simulated faults.
- Error trends reviewed in every test cycle.

### 26.3 AI Monitoring

- Routing distribution, per-agent latency, per-agent error rate, handoff counts tracked (AI_ARCHITECTURE.md §31.4).
- Token usage and cost/quota tracked per message/conversation/agent/model (AI_ARCHITECTURE.md §31.3).
- Evaluation metrics aggregated from logs + feedback (AI_ARCHITECTURE.md §38.2).

### 26.4 Performance Monitoring

- Latency percentiles (p50/p95/p99), TTFT, and end-to-end response times tracked (AI_ARCHITECTURE.md §31.2; API_SPECIFICATION.md §36.1).
- Performance budgets validated continuously (Section 16).

### 26.5 Database Monitoring

- Connection-pool usage, slow-query detection, and lock-wait behavior monitored (DATABASE_DESIGN.md §31).
- Retention/purge job success and duration monitored (DATABASE_DESIGN.md §35).

---

## 27. Test Environment

Test environments are isolated, reproducible, and clearly separated per the project's environment design (PROJECT_RULES.md Tech Stack — SQLite dev, PostgreSQL production; Docker orchestration). Environment isolation is a hard requirement — production data and credentials are never used for testing (BACKEND_ARCHITECTURE.md §26).

### 27.1 Development

| Aspect | Configuration |
| ------ | ------------- |
| **Purpose** | Day-to-day feature development and fast local testing. |
| **Database** | SQLite (dev), seeded with sample data. |
| **AI** | Mocked or gated LLM by default; real Gemini 2.5 Flash optional with explicit config. |
| **Vector store** | Local FAISS test index. |
| **Access** | Developers only; local machine or dev compose stack. |

### 27.2 Testing

| Aspect | Configuration |
| ------ | ------------- |
| **Purpose** | Run the automated suite (unit, integration, contract) continuously. |
| **Database** | Dedicated test database (PostgreSQL in CI-equivalent), reset per suite. |
| **AI** | Mocked LLM; golden prompt/retrieval fixtures. |
| **Vector store** | Dedicated test FAISS index, regenerated per run. |
| **Access** | CI runners and developers; fully isolated from other environments. |

### 27.3 Staging

| Aspect | Configuration |
| ------ | ------------- |
| **Purpose** | UAT, system/E2E suites, performance runs, and release-candidate validation. |
| **Database** | PostgreSQL with realistic seeded data (no real PII). |
| **AI** | Real Gemini 2.5 Flash permitted for E2E/UAT evaluation, with monitoring and budgets. |
| **Vector store** | Full or representative knowledge base index. |
| **Access** | Test team, students (UAT), supervisor review; mirrors production topology. |

### 27.4 Production

| Aspect | Configuration |
| ------ | ------------- |
| **Purpose** | Live service. |
| **Rules** | No automated tests run against production data or services. |
| **Validation** | Post-deployment smoke only (Section 21.3); monitored, never mutated by tests. |
| **AI** | Real LLM; guarded by the same guardrails validated in testing. |

### 27.5 Environment Isolation & Configuration

- All environment differences are configuration-driven (env files/settings) — never hardcoded (BACKEND_ARCHITECTURE.md §7).
- Environment variables differ per environment; `.env.example` is the template (PROJECT_RULES.md).
- Test credentials and seeds are never production credentials.
- Cross-environment leaks are prevented by connection-string separation and CI job isolation.

---

## 28. Test Automation Strategy

Test automation follows the **Automation First** principle (Section 1.4) and the CI readiness requirements in BACKEND_ARCHITECTURE.md §26 and API_SPECIFICATION.md §38. The `testing/` folder (e2e, integration, load) hosts the corresponding assets.

### 28.1 Automated Testing

- Unit, integration, API contract, RAG golden-set, and AI evaluation harness runs are fully automated.
- E2E critical journeys are automated; the full E2E suite runs on release candidates.
- Automation is versioned with the code and runs in CI on every change.

### 28.2 Manual Testing

- Reserved for: exploratory testing, UX/accessibility passes, device/browser passes (Sections 17–19), UAT (Section 22), and security review (Section 15).
- Manual passes follow documented checklists derived from ui-ux-design.md §41 and this document.
- Manual findings are logged as defects or improvements (Section 30).

### 28.3 Continuous Testing

- Tests run continuously in CI on every push, PR, and merge — not as a release-time afterthought.
- Fast suites gate every commit; slower suites gate merges and releases.
- Results feed quality gates (Section 31) automatically.

### 28.4 Test Scheduling

| Cadence | Suite |
| ------- | ----- |
| **Every push** | Fast unit + targeted integration for changed areas. |
| **Every PR** | Full unit + integration + API contract + smoke. |
| **Every merge to develop** | Full fast suite + E2E critical journeys + AI evaluation regression. |
| **Release candidate** | Full regression + performance + security pass + UAT. |
| **Periodic** | Load/stress cycles, browser/device matrix, security review. |

### 28.5 CI Readiness

- CI builds the project, runs the scheduled suites, and reports results (Section 32).
- External LLM calls are mocked or gated in CI (BACKEND_ARCHITECTURE.md §26).
- CI aborts on smoke failure (Section 21.2); quality gates block merges/releases (Section 31).
- CI artifacts (coverage, test reports, perf reports) are archived for traceability.

---

## 29. Test Coverage Standards

Coverage standards define the minimum expected coverage per area. Coverage is measured automatically and reported (Section 32); shortfalls block quality gates (Section 31).

| Area | Expected coverage | Notes |
| ---- | ----------------- | ----- |
| **Frontend** | All critical components and flows covered by component tests; critical journeys covered by E2E. | UI states and validation paths are high priority (ui-ux-design.md §41). |
| **Backend** | High branch/line coverage on services and repositories; every public service method tested. | Business rules and RBAC fully covered (BACKEND_ARCHITECTURE.md §26). |
| **Database** | Every table CRUD + constraints + key relationships; migrations covered. | Transactions and concurrency verified (DATABASE_DESIGN.md §34). |
| **APIs** | 100% of documented endpoints have contract tests (API_SPECIFICATION.md §15–24). | Status codes, errors, pagination/filter/sort covered (API_SPECIFICATION.md §38). |
| **AI** | 100% of intents and agents in the golden prompt set; evaluation metrics regression-protected. | Routing, hallucination, citations measured (AI_ARCHITECTURE.md §38). |
| **Critical features** | Auth, chat, RAG, and request workflow have automated coverage at every level they can support. | Definition of Done requires testability (PROJECT_RULES.md). |

**Rules:**
- Coverage is a floor, not a target ceiling — meaningful tests matter more than raw percentages.
- Untested critical paths are release blockers (Section 31).
- Coverage trends are tracked over time; regressions in coverage are addressed in the cycle.

---

## 30. Bug Management

Bug management governs how defects are recorded, prioritized, fixed, verified, and closed. It applies to defects found in any test level or environment.

### 30.1 Bug Severity

| Severity | Meaning |
| -------- | ------- |
| **Blocker** | System unusable, data loss/security issue, critical journey broken; release cannot proceed. |
| **High** | Major feature broken or degraded; workaround unavailable or unreasonable. |
| **Medium** | Feature partially broken or degraded; reasonable workaround exists. |
| **Low** | Minor cosmetic or UX polish; no functional impact. |

### 30.2 Bug Priority

| Priority | Meaning |
| -------- | ------- |
| **P1 — Immediate** | Fix before anything else; blocks the current cycle/release. |
| **P2 — This cycle** | Fix before release; scheduled in the current sprint. |
| **P3 — Soon** | Fix in a near-term cycle; tracked with normal backlog. |
| **P4 — Backlog** | Fix when convenient; low impact. |

Severity and priority are assessed together (e.g., a High-severity issue in a rarely used path may be P3; a Medium issue on the chat path may be P2).

### 30.3 Reporting

- Every bug is reported with: reproduction steps, expected vs. actual, environment, severity/priority, correlation IDs, and screenshots/logs where relevant.
- Bugs are linked to the failing requirement/feature and the test that caught them.
- AI defects include the golden-set query, routing signal, retrieval scores, and agent logs (AI_ARCHITECTURE.md §38.2).

### 30.4 Verification

- After a fix, the original test scenario is re-run; a regression test is added (Section 20.1).
- The fix is verified in the environment where the bug was found (or higher).
- Verification is performed by the tester, not only the fixer.

### 30.5 Closure Process

1. Bug reported and triaged (severity/priority assigned).
2. Fixed on a feature branch; the regression test is added.
3. All quality gates pass for the fix (Section 31).
4. Re-tested by the tester in the appropriate environment.
5. Closed with evidence; the fix is linked to the bug.

---

## 31. Quality Gates

Quality gates are the release criteria — every release candidate must pass all of them. They are enforced by CI and by the release process.

### 31.1 Build Success

- The project builds cleanly (frontend, backend, AI) with no type errors (strict TypeScript, proper Python typing) (PROJECT_RULES.md Definition of Done).

### 31.2 Test Pass Rate

- 100% of the scheduled automated suites pass on the release candidate (unit, integration, contract, E2E critical, AI evaluation regression).
- No known open Blocker/High defects (Section 30.1).

### 31.3 Performance Targets

- Performance budgets met at the documented percentiles (Section 16; API_SPECIFICATION.md §36.1).
- No perf regressions against the last recorded baseline.

### 31.4 Security Validation

- Security automated checks pass (Section 15); no known unresolved High security findings.
- Manual security review performed for the release; findings resolved or explicitly accepted.

### 31.5 AI Quality

- Evaluation metrics within thresholds: hallucination near zero, routing/retrieval/citation accuracy at targets (AI_ARCHITECTURE.md §38.1).
- No AI regression against the baseline (AI_ARCHITECTURE.md §38.3).

### 31.6 Documentation

- Feature documentation updated in `docs/` (PROJECT_RULES.md Definition of Done).
- The three source documents plus this strategy remain accurate for the released feature set.

---

## 32. Test Reporting

Test reporting keeps the team, supervisor, and stakeholders informed. Reports are part of the FYP evidence trail (AI_ARCHITECTURE.md §38.3 — Reporting).

### 32.1 Daily Reports

- Summarize the day's runs: suites executed, pass/fail, new defects, coverage deltas, blockers.
- Shared with the team to coordinate the next cycle.

### 32.2 Test Summary

- Per cycle/release: total tests, pass rate, suites executed, environments used, scope covered (Section 3).
- Statement of confidence: what was tested, what was not, and residual risk (Section 33).

### 32.3 Defect Summary

- Defects opened/closed, by severity/priority, open defect counts, average age, and verification status.
- Tracks defect density and closure trends over time.

### 32.4 Coverage Report

- Coverage per area (Section 29) with trends; gaps flagged for the next cycle.

### 32.5 Performance Report

- Latency percentiles, throughput, AI TTFT, token usage, and DB performance vs. budgets (Section 16).
- Included in release review and supervisor reports.

---

## 33. Risk Assessment

Risk assessment identifies testing risks and their mitigations. It is reviewed each cycle and updated when architecture or scope changes.

### 33.1 Technical Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Flaky tests degrade trust | False failures block progress | Deterministic tests, isolation (Section 1.5, 1.7), flake quarantine (Section 20.3). |
| Coverage gaps on hot paths | Regressions slip through | Coverage standards + gates (Sections 29, 31). |
| Environment drift | Tests pass locally, fail in CI | Reproducible environments (Section 27). |
| E2E fragility | Slow, brittle suites | Pyramid guidance (Section 1.3); few critical journeys (Section 21). |

### 33.2 AI Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Hallucination in production | Incorrect university guidance | Grounding rules, post-processing checks, evaluation metrics near zero hallucination (AI_ARCHITECTURE.md §20, §38). |
| Model/prompt drift | Quality regression | Versioned prompts + golden eval harness (Sections 10, 20.1). |
| Embedding/model change | Retrieval breakage | Golden retrieval set, re-embedding on change (Section 12.2). |
| LLM nondeterminism | Flaky AI tests | Mocked/gated LLM in automated suites (Section 23.2). |

### 33.3 Security Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Prompt injection/jailbreak | Compromised assistant behavior | Guardrails + adversarial test set (Sections 15.6, 23.3). |
| Data leakage across accounts | Privacy breach | Owner-scoping tests + RBAC matrix (Sections 15.2, 15.7). |
| Secret exposure in logs | Credential compromise | Log-safety rules and log review (Sections 25.1, 15.7). |

### 33.4 Database Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Transaction/concurrency bugs | Inconsistent state | Transaction and concurrency testing (Section 7.4). |
| Migration failures | Data loss/outage | Migration testing on empty + existing DBs (Section 7.5). |
| Retention misconfig | Legal/compliance issue | Retention policy tests (DATABASE_DESIGN.md §35; Section 7). |

### 33.5 Performance Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Load degradation | Poor UX under concurrency | Load/stress testing (Sections 16.5–16.6). |
| AI latency creep | Unacceptable response time | TTFT/latency monitoring + budgets (Sections 16.3, 26.4). |
| DB slowdown under growth | Page timeouts | Index validation + pagination efficiency (Sections 7.6–7.7). |

---

## 34. Future Testing Improvements

Future enhancements extend the testing strategy as the project grows (Phase 2–4, additional agents, integrations per PROJECT_RULES.md Future Scope). These are placeholders to be realized when the corresponding capabilities land.

### 34.1 AI-assisted Testing

- Automated generation of test cases, golden sets, and edge-case inputs from the requirement and architecture docs.
- AI-driven root-cause analysis of evaluation failures feeding the improvement loop (AI_ARCHITECTURE.md §38.3).

### 34.2 Visual Regression Testing

- Pixel-level comparison of UI against the design system (ui-ux-design.md §24 tokens) to catch unintended visual drift across releases and browsers.

### 34.3 Automated Accessibility Testing

- Fully automated WCAG AA scans on every build, complementing manual screen-reader passes (Section 17.4).

### 34.4 Continuous Performance Testing

- Performance testing in CI on every merge (not just release candidates), with trend-based alerting on budget regression.

### 34.5 Chaos Testing

- Fault injection into the AI, database, and network boundaries to validate recovery paths under real failure conditions (extending Section 24).

### 34.6 Penetration Testing

- Scheduled, credentialed penetration testing of the security architecture (Section 15), including prompt-injection and OWASP-class coverage as the platform adds integrations.

---

## Important

This document is the **permanent testing strategy** and the **single source of truth for all testing decisions** in the project.

It must be read together with:

- **PROJECT_RULES.md** — master project rules (Testing Standards, Definition of Done, workflows).
- **docs/architecture/BACKEND_ARCHITECTURE.md** — layer boundaries and the backend Testing Strategy (§26).
- **docs/architecture/DATABASE_DESIGN.md** — schema, transactions, retention, and concurrency contracts under test.
- **docs/architecture/AI_ARCHITECTURE.md** — agents, LangGraph, RAG, guardrails, and the evaluation metric framework (§38).
- **docs/architecture/API_SPECIFICATION.md** — endpoint contracts, error envelopes, and the API Testing Strategy (§38).
- **docs/architecture/ui-ux-design.md** — design tokens, UI states, and the UI Testing Checklist (§41).

All test planning, test suites, CI pipelines, quality-gate definitions, and quality-assurance workflows must be derived from this document. Any testing activity that deviates from this strategy must be corrected before it is accepted.

**This document is architecture and documentation only.** It contains no test code, no framework-specific code, no Python, and no SQL. Implementation is derived from these standards, following the project's Development Rules and Definition of Done.

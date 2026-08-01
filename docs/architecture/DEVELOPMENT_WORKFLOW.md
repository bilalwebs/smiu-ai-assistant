# DEVELOPMENT_WORKFLOW.md

**Agentic AI-Based University Workflow Automation System**
Multi-Agent Student Support Platform — developed for **Sindh Madressatul Islam University (SMIU)**

> Version: 1.0 · Status: Approved Architecture · Last Updated: August 2026 · Owner: Final Year Project Team
> Scope: Single source of truth for the complete software development lifecycle — philosophy, phases, task breakdown, Git workflow, coding standards, quality gates, release management, and collaboration.
> Sufficiently detailed that the entire development process — from planning to deployment — can be executed without additional workflow instructions.
> This document is **architecture and documentation only** — it contains no implementation code, no Python, no SQL, no Docker configuration, no Git commands, and no scripts.

---

## Table of Contents

1. [Development Philosophy](#1-development-philosophy)
2. [Development Goals](#2-development-goals)
3. [Software Development Lifecycle](#3-software-development-lifecycle)
4. [Project Development Phases](#4-project-development-phases)
5. [Milestone Planning](#5-milestone-planning)
6. [Task Breakdown Strategy](#6-task-breakdown-strategy)
7. [Development Order](#7-development-order)
8. [Git Workflow](#8-git-workflow)
9. [Branch Strategy](#9-branch-strategy)
10. [Commit Message Convention](#10-commit-message-convention)
11. [Pull Request Workflow](#11-pull-request-workflow)
12. [Code Review Guidelines](#12-code-review-guidelines)
13. [Coding Standards](#13-coding-standards)
14. [Folder Management Rules](#14-folder-management-rules)
15. [Dependency Management](#15-dependency-management)
16. [Environment Management](#16-environment-management)
17. [Configuration Management](#17-configuration-management)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Quality Standards](#19-code-quality-standards)
20. [Refactoring Strategy](#20-refactoring-strategy)
21. [Bug Management Workflow](#21-bug-management-workflow)
22. [Release Management](#22-release-management)
23. [Versioning Strategy](#23-versioning-strategy)
24. [Backup Strategy](#24-backup-strategy)
25. [Collaboration Guidelines](#25-collaboration-guidelines)
26. [Security During Development](#26-security-during-development)
27. [Performance Guidelines](#27-performance-guidelines)
28. [AI Development Workflow](#28-ai-development-workflow)
29. [Testing Workflow](#29-testing-workflow)
30. [Deployment Workflow](#30-deployment-workflow)
31. [Risk Management](#31-risk-management)
32. [Quality Gates](#32-quality-gates)
33. [Definition of Ready](#33-definition-of-ready)
34. [Definition of Done](#34-definition-of-done)
35. [Development Best Practices](#35-development-best-practices)
36. [Future Development Roadmap](#36-future-development-roadmap)

---

## 1. Development Philosophy

The development philosophy is the permanent set of engineering principles that governs every line of code and every workflow decision. It derives from the principles defined in **PROJECT_RULES.md** (Project Principles, Coding Standards) and the design philosophies in the architecture documents.

### 1.1 Clean Architecture

| Principle | Meaning |
| --------- | ------- |
| **Separation of concerns** | Presentation, business logic, data access, and AI concerns never mix in one class or file (BACKEND_ARCHITECTURE.md §2). |
| **Dependencies point inward** | Core domain logic never depends on frameworks, HTTP, or the database. |
| **Layer boundaries enforced** | Routers translate HTTP → service calls; routers never touch ORM, sessions, or queries (BACKEND_ARCHITECTURE.md §25). |
| **Feature isolation** | One service per feature; one responsibility per module (PROJECT_RULES.md Project Principles). |

### 1.2 SOLID Principles

| Principle | Application in this project |
| --------- | --------------------------- |
| **Single Responsibility** | Every module, service, component, and agent has exactly one reason to change. |
| **Open/Closed** | Extend behavior through configuration and new modules — never by modifying stable core logic. |
| **Liskov Substitution** | Repository/service abstractions are interchangeable; implementations honor their contracts. |
| **Interface Segregation** | Consumers depend on small, focused interfaces — not fat, general-purpose ones. |
| **Dependency Inversion** | High-level logic depends on abstractions; concrete implementations are injected (BACKEND_ARCHITECTURE.md §8). |

### 1.3 Modular Development

- Small, independent, well-bounded modules (PROJECT_RULES.md Project Principles).
- New features land in the existing folder structure — no parallel or duplicate structures (PROJECT_RULES.md Folder Structure).
- Reuse before writing: shared components, services, utilities, and prompts are the default (PROJECT_RULES.md Development Rules).

### 1.4 Scalability First

- Design for growth from day one (PROJECT_RULES.md Project Principles).
- The API is **stateless** — any number of instances can serve traffic; sessions and state live in the database (BACKEND_ARCHITECTURE.md §23).
- New agents are added by configuration, not new plumbing (BACKEND_ARCHITECTURE.md §31).
- Async-first, poolable connections, lazy loading of heavy AI initialization (BACKEND_ARCHITECTURE.md §23).

### 1.5 Maintainability

- Code that is easy to read, change, and extend (PROJECT_RULES.md Project Principles).
- Consistent patterns and naming across the entire codebase.
- Documentation is kept current as an intrinsic part of every change (Section 18).

### 1.6 Readability

- Meaningful names, small focused functions, no clever or opaque code.
- Comments explain **why**, not **what** (PROJECT_RULES.md Development Rules).
- Structure communicates intent before the reader reaches a single line of logic.

### 1.7 Simplicity

- Choose the simplest solution that works (PROJECT_RULES.md Project Principles).
- Never over-engineer; add complexity only when a real requirement demands it.
- Prefer small, focused modules over large, entangled ones.

### 1.8 Production-Ready Mindset

- No shortcuts, no throwaway code (PROJECT_RULES.md Project Principles).
- Every module is typed, tested, logged, documented, and deployable from day one (BACKEND_ARCHITECTURE.md §2).
- Definition of Done applies to every change, no matter how small (Section 34).

---

## 2. Development Goals

The goals below define what successful development looks like. Every phase, milestone, and task contributes to at least one goal.

### 2.1 Functional Goals

| Goal | Measure of success |
| ---- | ------------------ |
| Automate university workflows end to end | Admission, examination, and FAQ requests route, process, and resolve correctly (PROJECT_RULES.md Project Goal). |
| Deliver a multi-agent support platform | Coordinator routes to the correct specialist; specialists answer grounded in the knowledge base. |
| Complete Phase 1 scope | Landing, About, Contact, Auth, Dashboard, AI Chat, and the four agents (Coordinator, Admission, Examination, FAQ) fully functional (PROJECT_RULES.md Project Scope). |

### 2.2 Technical Goals

| Goal | Measure of success |
| ---- | ------------------ |
| Production-ready backend | Typed, tested, logged, containerized, deployable (BACKEND_ARCHITECTURE.md §1.4). |
| Clean, layered architecture | Strict dependency direction; no layer-skipping. |
| Single source of truth | Backend generated from BACKEND_ARCHITECTURE.md; schema from DATABASE_DESIGN.md; endpoints from API_SPECIFICATION.md; AI from AI_ARCHITECTURE.md. |
| Extensible agent platform | New agents added by configuration (BACKEND_ARCHITECTURE.md §31). |

### 2.3 AI Goals

| Goal | Measure of success |
| ---- | ------------------ |
| Grounded AI answers | RAG retrieval precedes every LLM response; sources cited (BACKEND_ARCHITECTURE.md §1.4). |
| Near-zero hallucination | Answers grounded in retrieved knowledge; no invented content (PROJECT_RULES.md AI Behaviour Rules; AI_ARCHITECTURE.md §20). |
| High routing/retrieval/citation accuracy | Metrics meet the AI_ARCHITECTURE.md §38 thresholds. |

### 2.4 Performance Goals

| Goal | Measure of success |
| ---- | ------------------ |
| Meet API budgets | Read/write/health endpoints sub-second at p95 (API_SPECIFICATION.md §36.1). |
| Meet AI latency budgets | TTFT optimized; latency percentiles tracked (AI_ARCHITECTURE.md §31.2). |
| Efficient database access | Indexed hot paths; keyset pagination; no full scans (DATABASE_DESIGN.md §31). |

### 2.5 Security Goals

| Goal | Measure of success |
| ---- | ------------------ |
| Secure by default | JWT auth, RBAC, input validation, secrets in env only (BACKEND_ARCHITECTURE.md §22). |
| No data leakage | Owner-scoped access; PII never exposed or logged (DATABASE_DESIGN.md §30; AI_ARCHITECTURE.md §30.2). |
| Resilient AI | Prompt-injection and jailbreak resistant (AI_ARCHITECTURE.md §26). |

### 2.6 Research Goals

| Goal | Measure of success |
| ---- | ------------------ |
| Research-grade engineering | Architecture and process themselves are FYP research contributions (BACKEND_ARCHITECTURE.md §1.4). |
| Documented evidence | Metrics, decisions, and results recorded in project reports (AI_ARCHITECTURE.md §38.3). |
| Defensible design choices | Every major decision traces to a documented rationale in the architecture docs. |

---

## 3. Software Development Lifecycle

The lifecycle is the end-to-end sequence every feature, phase, and release follows. It is a controlled, documented process — not ad-hoc activity.

### 3.1 Planning

| Activity | Output |
| -------- | ------ |
| Requirement clarification | Clear, testable requirements within Phase 1 scope. |
| Design review | The change is designed against the architecture docs before coding. |
| Task breakdown | Work decomposed into epics/features/tasks (Section 6). |
| Definition of Ready | The task is ready (Section 33). |

### 3.2 Architecture

- Every feature is derived from the relevant architecture source of truth (PROJECT_RULES.md Documentation Rules).
- Architecture changes are decided in the documents first, then code follows — never the reverse.
- The UI/UX architecture document is the only design source; design modifications update the document first (ui-ux-design.md §42).

### 3.3 Development

- Work proceeds on feature branches following the Git workflow (Sections 8–10).
- Code follows the coding standards (Section 13) and folder rules (Section 14).
- Tests are written with the code (Shift Left, TESTING_STRATEGY.md §1.2).

### 3.4 Testing

- The full testing strategy applies: unit, integration, system, E2E, acceptance (TESTING_STRATEGY.md §4).
- Quality gates validate each stage (Section 32).

### 3.5 Deployment

- Deployment follows the deployment workflow: build, validate, deploy, health check, rollback, monitor (Section 30).
- Smoke tests validate every deployed environment (TESTING_STRATEGY.md §21).

### 3.6 Maintenance

- Bugs, improvements, and future-scope features are handled through the documented workflows (Sections 20–21).
- Monitoring and feedback loops drive continuous improvement (AI_ARCHITECTURE.md §38.3).

---

## 4. Project Development Phases

The project is developed in ordered phases (PROJECT_RULES.md Project Workflow). Each phase builds on the previous one — do not skip ahead.

| Phase | Name | Deliverable |
| ----- | ---- | ----------- |
| **Phase 1** | Project Setup | Repository structure, environment config, Docker skeleton, CI foundation, folder scaffold per PROJECT_RULES.md. |
| **Phase 2** | Backend Foundation | FastAPI app shell, layered architecture (api/core/models/schemas/services/middleware), configuration, DI, logging. |
| **Phase 3** | Authentication | JWT auth, sessions, RBAC, registration/login, password reset, email verification (API_SPECIFICATION.md §3–5). |
| **Phase 4** | Database | Models, migrations, seeds for all 16 tables per DATABASE_DESIGN.md; transaction and repository layer. |
| **Phase 5** | Knowledge Base | Knowledge folder structure, document ingestion, chunking, metadata, FAISS indexing (AI_ARCHITECTURE.md §36). |
| **Phase 6** | AI System | Coordinator/Admission/Examination/FAQ agents, LangGraph workflow, RAG pipeline, prompts, guardrails. |
| **Phase 7** | Frontend | Next.js app, shared components, pages per ui-ux-design.md, chat interface, auth flows, dashboards. |
| **Phase 8** | Testing | Full test suites, evaluation harness, performance runs, UAT (TESTING_STRATEGY.md). |
| **Phase 9** | Deployment | Docker images, compose stacks, CI/CD, staging validation, release. |
| **Phase 10** | Future Improvements | Roadmap items (Section 36) and future-scope agents (PROJECT_RULES.md Future Scope). |

**Phase rules:**
- Phases proceed in order; a phase is complete only when its Definition of Done is met (Section 34).
- Cross-cutting concerns (security, logging, tests, documentation) are built into every phase — never deferred wholesale.

---

## 5. Milestone Planning

Milestones are the major checkpoints of the project. Each milestone has defined entry/exit criteria and is reviewed with the supervisor.

| Milestone | Exit criteria |
| --------- | ------------- |
| **Architecture Complete** | All architecture source documents approved: UI/UX, Backend, Database, AI, API, Testing, Development Workflow. |
| **Backend Complete** | FastAPI foundation, auth, services, repositories, middleware all implemented and tested (Phases 2–4). |
| **Database Complete** | All 16 tables, migrations, seeds, transactions implemented and validated (Phase 4). |
| **AI Complete** | Four agents, LangGraph workflow, RAG pipeline, prompts, guardrails working end to end (Phase 6). |
| **Frontend Complete** | All pages and components implemented per ui-ux-design.md, responsive and accessible (Phase 7). |
| **Testing Complete** | Full test suites green, evaluation metrics baseline captured, performance validated (Phase 8). |
| **Deployment Ready** | Containerized stack deploys cleanly; staging validated by smoke tests (Phase 9). |
| **Final Submission** | All FYP deliverables (documents, reports, demo, code) complete and accepted. |

**Milestone rules:**
- Each milestone is planned with a schedule and owner.
- A milestone is never declared complete on intent — only on verified exit criteria (Section 34).

---

## 6. Task Breakdown Strategy

Work is decomposed into a strict hierarchy. Every unit of work belongs to exactly one level.

| Level | Definition | Example |
| ----- | ---------- | ------- |
| **Epic** | A large body of work spanning phases, tracked as a milestone grouping. | "AI System (Phase 6)". |
| **Feature** | A user-visible capability within an epic. | "AI chat with RAG-backed answers". |
| **Task** | A unit of development work that implements part of a feature. | "Implement Admission Agent retrieval node". |
| **Subtask** | The smallest actionable step of a task. | "Add retrieval metadata filter for category". |
| **Bug** | A defect in implemented functionality (Section 21). | "Chat history shows wrong message count". |
| **Hotfix** | An urgent production/staging defect requiring immediate release (Section 22). | "Auth session expiry regression". |
| **Research Task** | A study/investigation unit producing a documented decision. | "Evaluate chunk size for admission documents". |

**Breakdown rules:**
- Epics → features → tasks → subtasks; a task is ready when its Definition of Ready is met (Section 33).
- Tasks are small enough to complete and review within a short cycle.
- Research tasks produce a documented finding that feeds a decision — never unspecified code changes.

---

## 7. Development Order

The recommended implementation order defines *what gets built first*. It follows the dependency structure of the project (PROJECT_RULES.md Project Workflow).

| Order | Area | Rationale |
| ----- | ---- | --------- |
| 1 | **Project Setup** | Folder structure, tooling, env config, CI skeleton — everything else depends on it. |
| 2 | **Database** | Schema, migrations, seeds ground the backend and AI persistence (DATABASE_DESIGN.md). |
| 3 | **Authentication** | Auth gates every protected surface; needed before students and dashboards. |
| 4 | **Backend APIs** | Core endpoints and services implementing the business logic (API_SPECIFICATION.md). |
| 5 | **Knowledge Base** | Ingestion, chunking, and indexing must exist before RAG can retrieve. |
| 6 | **AI Agents** | Coordinator and specialists built on the RAG pipeline and auth. |
| 7 | **Frontend** | Pages and components consume the completed backend and AI. |
| 8 | **Testing** | Full suites, evaluation harness, and performance validation. |
| 9 | **Deployment** | Containerization, CI/CD, and release. |

**Order rules:**
- Do not skip ahead; each area builds on the previous one (PROJECT_RULES.md Project Workflow).
- Within an area, vertical slices (a feature end to end) are preferred over horizontal layers where practical.

---

## 8. Git Workflow

The Git workflow governs how the repository is used day to day. It follows the Git & Version Control Standards in PROJECT_RULES.md and is designed for a small FYP team using GitHub.

### 8.1 Repository Structure

| Aspect | Convention |
| ------ | ---------- |
| Remote | GitHub repository owned by the project. |
| Default branch | `main` — production-ready, always deployable. |
| Protected branches | `main` (and `develop` when used) protected from direct pushes; changes arrive via Pull Request (Section 11). |
| Repository layout | Standard project layout per PROJECT_RULES.md Folder Structure. |

### 8.2 Clone

- Developers clone the repository once and keep it synchronized.
- Always start work from an up-to-date base branch (`develop` or the relevant feature base).

### 8.3 Branch

- A new branch is created for every unit of work (feature/bugfix/hotfix/release) using the naming convention (Section 9).
- One branch per feature — never mix unrelated work on one branch (PROJECT_RULES.md).

### 8.4 Commit

- Small, focused commits with meaningful messages (Section 10).
- Commit only related changes; no "kitchen sink" commits.
- Never commit secrets, generated artifacts, or local configuration (Section 26).

### 8.5 Push

- Commits are pushed to the feature branch regularly to enable review and backup.
- Pushes to `main`/`develop` are never direct — only through reviewed Pull Requests.

### 8.6 Merge

- Merges occur through Pull Requests after review and green quality gates (Sections 11, 32).
- Merge conflicts are resolved locally on the feature branch before merge (Section 11.5).

### 8.7 Release

- Releases are cut from `main` via a `release/*` branch following the release management process (Sections 22–23).

---

## 9. Branch Strategy

Branch naming is standardized. Every branch type has a fixed prefix and purpose.

| Branch | Naming | Purpose |
| ------ | ------ | ------- |
| `main` | `main` | Production-ready, always deployable (PROJECT_RULES.md). |
| `develop` | `develop` | Integration branch for completed features. |
| Feature | `feature/<slug>` | One branch per feature; branched from `develop`. |
| Bugfix | `bugfix/<slug>` | Non-urgent defect fix; branched from `develop`. |
| Hotfix | `hotfix/<slug>` | Urgent production defect; branched from `main`, merged to `main` and `develop`. |
| Release | `release/<version>` | Release preparation and validation; branched from `develop` (Section 22). |

**Rules:**
- Slugs are short, descriptive, and `kebab-case` (e.g., `feature/ai-chat`, `bugfix/chat-history-count`).
- Branches are short-lived; they are deleted after merge.
- Never push broken code to `main` or `develop` (PROJECT_RULES.md).

---

## 10. Commit Message Convention

Commit messages follow the Conventional Commits style. Each message is one concise, meaningful sentence describing *what* and *why* (PROJECT_RULES.md).

### 10.1 Message Format

```
<type>(<optional scope>): <short summary>
```

### 10.2 Commit Types

| Type | Usage |
| ---- | ----- |
| `feat` | A new feature or user-visible capability. |
| `fix` | A bug fix. |
| `docs` | Documentation changes (docs/, README, inline docs). |
| `style` | Formatting, whitespace, naming — no behavior change. |
| `refactor` | Code change that neither fixes a bug nor adds a feature. |
| `test` | Adding or updating tests. |
| `perf` | A performance improvement. |
| `build` | Build system or dependency changes (Docker, package manifests). |
| `ci` | CI configuration and scripts. |
| `chore` | Routine maintenance; no functional change. |

### 10.3 Examples

- `feat(chat): add streaming AI responses`
- `fix(auth): reject expired refresh tokens`
- `docs(db): document retention windows`
- `refactor(agents): extract shared context builder`
- `test(api): cover pagination edge cases`

**Rules:**
- One logical change per commit.
- The message explains *what* and *why*, not only *what changed*.
- Scopes align with areas (auth, chat, agents, rag, db, api, ui, docs, ci).

---

## 11. Pull Request Workflow

Pull Requests are the only path into `main`/`develop`. They ensure review, validation, and traceability (PROJECT_RULES.md Git Standards).

### 11.1 PR Creation

| Requirement | Detail |
| ----------- | ------ |
| Base | Feature branches target `develop`; hotfix/release target `main`. |
| Description | What, why, how; links to the task/bug; test evidence. |
| Size | Small and reviewable — one feature/fix per PR. |
| CI | All automated suites (TESTING_STRATEGY.md §28.5) pass before review. |
| DoD | Definition of Done checklist (Section 34) is complete. |

### 11.2 PR Review

- Review follows the Code Review Guidelines (Section 12).
- At least one reviewer besides the author must approve non-trivial changes.
- Reviewer verifies architecture compliance, security, and tests — not just code style.

### 11.3 Approval

- Approval is given only when the review checklist passes and quality gates are green (Section 32).
- Requests for changes are resolved with commits on the same branch; the branch is rebased/updated as needed.

### 11.4 Merge

- Approved PRs are merged (squash merge recommended for clean history).
- Merging to `develop` triggers CI; merging to `main` is a release event (Section 22).

### 11.5 Conflict Resolution

- Conflicts are resolved locally on the feature branch against the current base — never by force-pushing over teammates' work.
- After resolving, the relevant tests re-run before the merge.
- Large, conflict-prone branches are rebased/updated frequently to stay close to the base.

---

## 12. Code Review Guidelines

Reviews evaluate the change against the criteria below. They are part of the quality gates (Section 32).

| Criterion | Review questions |
| --------- | ---------------- |
| **Readability** | Is the code clear and self-documenting? Would a new teammate understand it? |
| **Maintainability** | Is the change easy to modify later? Does it follow existing patterns? |
| **Architecture compliance** | Does it respect layer boundaries, folder structure, and the source docs (Sections 13–14)? |
| **Security** | Any secrets, injection vectors, auth/authorization gaps, or data-leak risks (Section 26)? |
| **Performance** | Any N+1 queries, missing indexes, blocking calls on hot paths, or token waste (Section 27)? |
| **Testing** | Are tests written with the change? Do they cover the behavior and edge cases (TESTING_STRATEGY.md)? |
| **Documentation** | Is the relevant documentation updated (Section 18)? |

**Review rules:**
- Reviews are constructive, specific, and objective.
- Reviewers verify behavior, not just style.
- Automated checks (lint, type, tests) are the baseline; reviewers focus on what machines cannot judge.

---

## 13. Coding Standards

Coding standards are the enforceable rules for how code is written. They derive from PROJECT_RULES.md Coding Standards and the architecture documents.

### 13.1 Python

- Strict type hints on all functions and models; Pydantic for schemas (PROJECT_RULES.md Coding Standards).
- Modules, classes, and public functions documented (Google/NumPy style) (BACKEND_ARCHITECTURE.md §25).
- One responsibility per file; one service per feature (BACKEND_ARCHITECTURE.md §25).
- Async-first for I/O; no blocking calls in async handlers (BACKEND_ARCHITECTURE.md §23).
- No business logic in routers; routers never touch ORM (BACKEND_ARCHITECTURE.md §25).

### 13.2 TypeScript

- Strict typing, explicit interfaces/types, no `any`, no unused code (PROJECT_RULES.md Coding Standards).
- Components `PascalCase`; hooks `use`-prefixed `camelCase`; functions/variables `camelCase`; constants `UPPER_CASE` (PROJECT_RULES.md Naming Conventions).
- No implicit or `any`-typed code; shared types centralized.

### 13.3 React

- Reusable shadcn/ui primitives and feature-level composites (ui-ux-design.md §10, §25).
- Logic, UI, and API calls separated — never mixed in one component (PROJECT_RULES.md Coding Standards).
- Server actions/API routes for sensitive logic (auth, database, LLM) — never client-side (PROJECT_RULES.md Coding Standards).
- Loading, empty, and error states on every async component (ui-ux-design.md §29).

### 13.4 FastAPI

- Pydantic v2 validation at every boundary (BACKEND_ARCHITECTURE.md §14).
- Dependency injection for sessions and services (BACKEND_ARCHITECTURE.md §8).
- Consistent error handling via centralized exception handlers (BACKEND_ARCHITECTURE.md §15).
- Endpoints documented (schemas, error responses) per API_SPECIFICATION.md §30.

### 13.5 Naming

| Layer | Convention |
| ----- | ---------- |
| Python files/functions/variables | `snake_case` |
| Python classes | `PascalCase` |
| Constants | `UPPER_CASE` / `SCREAMING_SNAKE_CASE` |
| Database tables/columns | `snake_case` |
| API endpoints | `kebab-case` |
| TypeScript components/types/interfaces | `PascalCase` |
| Hooks/functions/variables | `camelCase` |
| Pages/routes | `kebab-case` |

### 13.6 Formatting

- Consistent formatting enforced by tooling (formatter + lint in CI).
- One obvious formatting style project-wide; no per-developer drift.

### 13.7 Comments

- Comments explain *why*, not *what* (PROJECT_RULES.md Development Rules).
- No redundant comments that restate the code.
- Architecture-relevant "why" decisions are also recorded in the docs.

### 13.8 Imports

- Imports grouped and ordered consistently; no unused imports.
- Import from the layer above/downward only — never upward or sideways across boundaries (BACKEND_ARCHITECTURE.md §25).

---

## 14. Folder Management Rules

Folder management keeps the codebase navigable and prevents duplication. It follows the **standard project layout** in PROJECT_RULES.md — every new file must land in the correct folder.

### 14.1 Folder Organization

| Folder | Ownership |
| ------ | --------- |
| `frontend/` | UI only — Next.js pages, components, hooks, types, styling. |
| `backend/` | API and business logic — routes, schemas, services, models, middleware. |
| `ai/` | Agents, LangGraph, RAG — agents, graphs, chains, tools, memory, retrieval, prompts. |
| `database/` | Schema, migrations, seeds. |
| `knowledge/` | University documents and FAQs (source files for RAG). |
| `docs/` | Architecture and documentation. |
| `docker/` | Deployment configuration. |
| `testing/` | Test assets (e2e, integration, load). |
| `scripts/` | Automation scripts — setup, seed, maintenance. |

### 14.2 File Placement

- Every file has a clear owner and purpose; no parallel or duplicate structures (PROJECT_RULES.md).
- Files land only in the folder that owns their concern.
- Never create unnecessary files or folders (PROJECT_RULES.md).

### 14.3 Feature Modules

- Features are composed of small, well-bounded modules within their owning layer.
- One service per feature (backend); feature-level components compose shared primitives (frontend).

### 14.4 Shared Components

- Reusable UI lives in the shared component library (shadcn/ui + feature composites) (ui-ux-design.md §25, §38).
- Search before creating; extract shared parts; never duplicate markup (ui-ux-design.md §43).

### 14.5 Utilities

- Shared helpers live in designated utility folders (`lib`, `utils`) and are reused before anything new is written.
- Utilities are generic and layer-appropriate — never business logic in disguise.

### 14.6 Configuration

- Configuration lives in environment/configuration files (Section 16–17), never scattered in code.
- `.env.example` is the single template for environment variables (PROJECT_RULES.md Environment Variables).

---

## 15. Dependency Management

Dependency management keeps the stack consistent, secure, and reproducible across environments.

### 15.1 Python Packages

- Backend/AI dependencies are declared in the backend requirements manifests (split by purpose: runtime, dev, testing).
- Versions are pinned to the tested set; upgrades are deliberate and reviewed (Section 15.4).

### 15.2 Node Packages

- Frontend dependencies declared in the package manifest with a lockfile committed to the repository.
- Dependency changes arrive via reviewed PRs, not ad-hoc local installs.

### 15.3 Version Locking

- Lockfiles are committed so every environment installs the identical dependency set.
- CI installs from the lockfile — never a floating latest resolution.
- A clean install from the lockfile reproduces the developer environment (TESTING_STRATEGY.md §27).

### 15.4 Updates

- Dependency updates are regular, reviewed, and small.
- Security-relevant updates are prioritized and validated (Section 26.4).
- Updates are regression-tested before merge (TESTING_STRATEGY.md §20).

### 15.5 Unused Dependencies

- Unused dependencies are removed, not left in place (PROJECT_RULES.md — no unnecessary files).
- New dependencies require justification in the PR: purpose, alternatives considered, size/risk.
- Dependency audits (licenses, vulnerabilities) run in CI.

---

## 16. Environment Management

Environment management separates the four environments and keeps their configuration isolated (TESTING_STRATEGY.md §27).

| Environment | Database | AI | Purpose |
| ----------- | -------- | -- | ------- |
| **Development** | SQLite (dev) | Mocked/gated LLM by default | Local feature development. |
| **Testing** | Dedicated test DB (PostgreSQL) | Mocked LLM | Automated suites in CI. |
| **Staging** | PostgreSQL, realistic seeded data | Real Gemini 2.5 Flash | UAT, E2E, performance, release validation. |
| **Production** | PostgreSQL | Real LLM | Live service; never touched by tests. |

### 16.1 Environment Variables

- All secrets/config load from `.env` (gitignored); `.env.example` holds the template (PROJECT_RULES.md Environment Variables).
- Every new variable is added to `.env.example` when introduced.
- Environment differences are configuration-driven — never hardcoded (Section 17).

### 16.2 Secrets Management

- Secrets are never hardcoded or committed (Section 26).
- Test/CI credentials are separate from any real credentials.
- Never log secrets, API keys, tokens, or passwords (PROJECT_RULES.md Logging & Monitoring).

### 16.3 Configuration Separation

- Each environment has its own configuration scope (env files/settings), never shared mutable config.
- Staging mirrors production topology so release validation is meaningful (TESTING_STRATEGY.md §27).

---

## 17. Configuration Management

Configuration is centralized, typed, and environment-aware (BACKEND_ARCHITECTURE.md §7).

| Configuration type | Contents |
| ------------------ | -------- |
| **Application** | App settings, logging levels, CORS allow-list, security headers. |
| **AI** | Model name (Gemini 2.5 Flash), temperature, context budget, `CHAT_HISTORY_LIMIT`, `RAG_TOP_K`, thresholds (AI_ARCHITECTURE.md §17.3, §21.6). |
| **Database** | Connection string, pool sizing, isolation settings, migration config (DATABASE_DESIGN.md §31, §34). |
| **API** | Timeouts, pagination defaults, rate limits, idempotency windows (API_SPECIFICATION.md §9, §13, §34, §36). |
| **Feature flags** | Opt-in long-term memory, streaming, and future capabilities gated by flags (Section 17.1). |

### 17.1 Feature Flags

- Optional/mature features (long-term memory, streaming, future agents) are configuration-gated.
- Flags default off for unproven capabilities and are turned on only after validation.
- Flag decisions are documented in the relevant architecture doc.

---

## 18. Documentation Standards

Documentation is a first-class deliverable (PROJECT_RULES.md Documentation Rules). Every feature is documented before it is considered done.

### 18.1 Architecture Documents

- The architecture source documents are the permanent single sources of truth (PROJECT_RULES.md; each doc's Important section).
- Architecture changes are reflected in the documents first, then code.
- The doc index (`docs/README.md`) lists the architecture source documents.

### 18.2 API Documentation

- Every endpoint documented per API_SPECIFICATION.md §30 (OpenAPI docs + schemas + error responses).
- API docs match implemented behavior (validated in tests, API_SPECIFICATION.md §38).

### 18.3 Database Documentation

- Schema decisions derived from DATABASE_DESIGN.md; migrations stay consistent with it.
- Changes to schema update the database doc before code.

### 18.4 AI Documentation

- Every agent has its own documentation; prompts are versioned and tracked like code (PROJECT_RULES.md Prompt Engineering Rules).
- AI behavior follows AI_ARCHITECTURE.md and is documented accordingly.

### 18.5 README

- The root README explains the project, setup, and links to the documentation.
- Setup/run instructions are accurate for the current state.

### 18.6 Inline Documentation

- Python docstrings on modules/classes/functions (Google/NumPy style) (BACKEND_ARCHITECTURE.md §25).
- Comments explain *why*, not *what* (Section 13.7).
- No documentation that restates code; documentation that explains intent.

---

## 19. Code Quality Standards

Code quality standards are the non-negotiable baseline for every commit (PROJECT_RULES.md Project Principles, Definition of Done).

| Standard | Rule |
| -------- | ---- |
| **Consistency** | Same patterns, naming, and structure everywhere in the codebase. |
| **Reusability** | Reuse before writing; extract shared parts; no duplication (PROJECT_RULES.md Development Rules). |
| **Modularity** | Small, focused modules with single responsibilities. |
| **Maintainability** | Easy to read, change, and extend; documented where needed. |
| **Performance** | No obvious waste: N+1 queries, blocking I/O in async paths, oversized payloads. |
| **Security** | Validation at boundaries, no secrets, correct auth/authorization. |
| **Readability** | Meaningful names, clear structure, self-documenting logic. |

---

## 20. Refactoring Strategy

Refactoring keeps the codebase healthy without breaking behavior.

### 20.1 When to Refactor

- Duplication detected during review or development (extract shared code).
- A module has grown beyond a single responsibility.
- The codebase pattern has evolved and an area lags it.
- Complexity blocks adding a required feature.
- Never refactor without a driving need (simplicity principle, Section 1.7).

### 20.2 Refactoring Rules

- Refactoring is a separate, focused change — never mixed with feature work in one commit.
- Prefer updating existing files over creating new ones (PROJECT_RULES.md).
- Refactoring keeps public contracts (API, DB schema, agent behavior) stable unless deliberately versioned otherwise.

### 20.3 Safe Refactoring

- Refactor behind the protection of the existing test suite (TESTING_STRATEGY.md §20).
- Small, incremental steps with tests passing after each step.
- Behavior-preserving changes verified by regression tests before merge.

### 20.4 Regression Prevention

- Every refactor runs the full relevant regression suite (unit, integration, API contract).
- A behavior change discovered during refactor is a separate bug — tracked and fixed separately (Section 21).

---

## 21. Bug Management Workflow

Bugs are managed through the documented workflow (TESTING_STRATEGY.md §30). This section describes the team process.

### 21.1 Bug Reporting

- Every bug is reported with reproduction steps, expected vs. actual, environment, severity, and evidence (logs, correlation IDs, screenshots) (TESTING_STRATEGY.md §30.3).
- Bugs link to the failing feature and the test that caught them.

### 21.2 Bug Classification

- Severity (Blocker/High/Medium/Low) and priority (P1–P4) are assigned at triage (TESTING_STRATEGY.md §30.1–30.2).

### 21.3 Priority

- P1 blocks the current cycle/release; P2 is fixed before release; P3/P4 are scheduled/backlogged.

### 21.4 Assignment

- Bugs are assigned to the owner of the affected area (frontend/backend/AI/database).
- Blockers are triaged immediately; the assignee is responsible for the fix cycle.

### 21.5 Resolution

- Fix on a `bugfix/*` branch (or `hotfix/*` for urgent production issues, Section 22).
- The fix includes a regression test (TESTING_STRATEGY.md §20.1).

### 21.6 Verification

- Re-tested by the tester in the environment where it was found (or higher).
- Verification is independent of the fixer (TESTING_STRATEGY.md §30.4).

### 21.7 Closure

- Closed with evidence once verification passes and quality gates are green (TESTING_STRATEGY.md §30.5).

---

## 22. Release Management

Releases are controlled, validated events. They follow the versioning strategy (Section 23) and deployment workflow (Section 30).

### 22.1 Release Planning

- A release is scoped: version, features, fixes, acceptance criteria, schedule.
- Release candidates are scheduled from `develop` via a `release/<version>` branch.

### 22.2 Release Validation

- Full regression, performance, and security suites run on the release candidate (TESTING_STRATEGY.md §31).
- Staging validation: E2E critical journeys, smoke tests, UAT sign-off (TESTING_STRATEGY.md §21–22).
- AI evaluation metrics checked against the baseline (AI_ARCHITECTURE.md §38.3).

### 22.3 Release Checklist

- All quality gates green (Section 32).
- No open Blockers/High defects (TESTING_STRATEGY.md §30.1).
- Documentation updated for the released scope (Section 18).
- Version bumped per semantic versioning (Section 23).
- Backup verified before release (Section 24).

### 22.4 Version Release

- Merge `release/<version>` to `main`; tag the version (Section 23).
- Post-deployment smoke validates the deployed environment (TESTING_STRATEGY.md §21.3).
- Hotfixes merge to `main` and `develop`.

### 22.5 Rollback Strategy

- Every release has a documented rollback path: previous stable version/images and database backup.
- Rollback is initiated when smoke/monitoring detects a critical failure post-deploy.
- Post-rollback analysis drives a corrective release.

---

## 23. Versioning Strategy

Versioning follows Semantic Versioning (MAJOR.MINOR.PATCH) with release-candidate tags.

| Version component | Bump when |
| ----------------- | --------- |
| **MAJOR** | Breaking API, schema, or behavior changes. |
| **MINOR** | Backward-compatible new features or capability additions. |
| **PATCH** | Backward-compatible bug fixes and minor changes. |
| **Release Candidate** | Pre-release builds: `MAJOR.MINOR.PATCH-rc.N` (e.g., `1.0.0-rc.1`). |

**Rules:**
- `main` always carries the current released version; `develop` tracks the next unreleased version.
- Version tags in Git match the release (Section 22.4).
- API versioning (`/api/v1`) is independent of package versioning and governed by API_SPECIFICATION.md §14.

---

## 24. Backup Strategy

Backups protect all project assets. They are verified, not just scheduled.

| Asset | Strategy |
| ----- | -------- |
| **Source code** | GitHub repository (authoritative); feature branches pushed regularly; no work exists only locally. |
| **Database** | Regular snapshots/backups per DATABASE_DESIGN.md §29; restore verified periodically. |
| **Documentation** | Documentation lives in the repository (`docs/`) and is backed up with source control. |
| **Knowledge base** | Source documents under `knowledge/` are versioned in the repo; the FAISS index is regenerable (DATABASE_DESIGN.md §35 — regenerable data exempt from retention). |
| **Configuration** | Environment templates (`.env.example`) in the repo; actual secrets managed securely and recoverable (Section 26.2). |

**Rules:**
- Backups are tested by restore, not just created.
- The vector store is treated as derived data — always recoverable from `knowledge/` + chunk metadata (DATABASE_DESIGN.md §21).

---

## 25. Collaboration Guidelines

Collaboration standards keep the FYP team effective and the project coherent.

### 25.1 Communication

- Decisions are recorded in the documentation; async communication defaults to issues/PRs for traceability.
- Blocking questions are raised early; assumptions are never silently made.

### 25.2 Task Assignment

- Work is assigned from the breakdown structure (Section 6); each task has one owner.
- Owners are responsible for the full cycle: implement, test, document, review, close.

### 25.3 Documentation Updates

- The person who changes behavior updates the docs in the same change (Section 18).
- Architecture documents are updated before code when they define the behavior.

### 25.4 Code Ownership

- Each area has an owner (frontend/backend/AI/database), but all code passes review (Section 12).
- Shared components, utilities, and prompts are team-owned and reviewed like code.

### 25.5 Knowledge Sharing

- Reviews, documentation, and the evaluation loop (AI_ARCHITECTURE.md §38.3) are the sharing mechanisms.
- Research findings are documented (Section 6 — Research Tasks) so decisions are reusable.

---

## 26. Security During Development

Security is built into the development process, not bolted on at release.

### 26.1 Secrets Protection

- Secrets never hardcoded or committed; loaded only from environment (PROJECT_RULES.md Environment Variables).
- Secret-scanning runs in CI to catch accidental commits.

### 26.2 Git Ignore Rules

- `.gitignore` covers: `.env`, local databases, generated artifacts, the FAISS vectorstore (`knowledge/vectorstore/`), node_modules, build output, caches.
- Files that must never be committed are confirmed in `.gitignore` before pushing.

### 26.3 Credential Management

- Real credentials are never used in tests, CI, or documentation.
- Staging/UAT credentials are separate and clearly non-production.

### 26.4 Dependency Security

- Dependencies are audited (vulnerabilities, licenses) in CI (Section 15.4).
- Security-relevant updates are prioritized and validated.

### 26.5 Secure Coding

- Validation at every boundary (client + server) (PROJECT_RULES.md Coding Standards).
- Parameterized/ORM queries only — never string-built SQL (BACKEND_ARCHITECTURE.md §22).
- Output escaped/sanitized; no unsafe HTML (BACKEND_ARCHITECTURE.md §22).
- Least privilege and default-deny for roles and access (BACKEND_ARCHITECTURE.md §10, §22).
- Security testing per TESTING_STRATEGY.md §15.

---

## 27. Performance Guidelines

Performance is designed in, then verified continuously (TESTING_STRATEGY.md §16).

### 27.1 Efficient Code

- Async-first, non-blocking I/O in the backend (BACKEND_ARCHITECTURE.md §23).
- Lazy loading of heavy AI initialization and non-critical UI (BACKEND_ARCHITECTURE.md §23).
- No redundant recomputation or duplicated work in hot paths.

### 27.2 Database Optimization

- Query only what is needed; paginate large lists (PROJECT_RULES.md Performance & Security).
- Indexed hot paths; keyset pagination; efficient counts (DATABASE_DESIGN.md §31).
- Batch operations in single transactions — no commit-per-row (DATABASE_DESIGN.md §34.3).

### 27.3 API Optimization

- Response payloads bounded by pagination and field selection (API_SPECIFICATION.md §36.6).
- Compression and caching headers per API_SPECIFICATION.md §36.3–36.4.
- Background jobs for long operations — never synchronous (API_SPECIFICATION.md §36.2).

### 27.4 Frontend Optimization

- Lazy loading and code splitting for route-level bundles (PROJECT_RULES.md Performance & Security).
- Images optimized; layout-stable skeletons (CLS-safe) (ui-ux-design.md §41).
- Performance budget per ui-ux-design.md §32.

### 27.5 AI Optimization

- Concise, modular prompts to reduce input tokens (AI_ARCHITECTURE.md §32.1).
- Metadata filtering, top-K tuning, in-memory index (AI_ARCHITECTURE.md §32.2).
- Caching where appropriate; token usage tracked (AI_ARCHITECTURE.md §31.3).

---

## 28. AI Development Workflow

AI development follows the AI architecture (AI_ARCHITECTURE.md), prompt rules (PROJECT_RULES.md Prompt Engineering Rules), and the AI testing strategy (TESTING_STRATEGY.md §10–13).

### 28.1 Prompt Development

- Prompts live in `ai/prompts/` — never hardcoded in routes (PROJECT_RULES.md).
- Every agent owns its prompt; reusable prompt components over duplicated text.
- Prompts are versioned and tracked like code (PROJECT_RULES.md).

### 28.2 Prompt Review

- Prompts are reviewed like code: accuracy, tone, grounding rules, guardrails, formatting (AI_ARCHITECTURE.md §13, §27).
- Prompt changes are regression-tested via the evaluation harness (AI_ARCHITECTURE.md §38.3).

### 28.3 Agent Development

- Agents are built within `ai/agents/` following the existing structure (PROJECT_RULES.md AI Agents).
- New Phase-1 agents: Coordinator, Admission, Examination, FAQ. Future agents are placeholders only (PROJECT_RULES.md).
- Agent behavior derives from AI_ARCHITECTURE.md and is tested per TESTING_STRATEGY.md §10–11.

### 28.4 RAG Development

- RAG pipeline built per AI_ARCHITECTURE.md §14–19 and BACKEND_ARCHITECTURE.md §21.
- Retrieval is tested with golden sets; grounding and citations are verified (TESTING_STRATEGY.md §12).

### 28.5 Knowledge Base Updates

- Knowledge changes follow the ingestion/versioning rules (AI_ARCHITECTURE.md §36; DATABASE_DESIGN.md §20–21).
- Updates trigger re-indexing and retrieval regression (TESTING_STRATEGY.md §13.5–13.6).

### 28.6 Evaluation

- The evaluation loop (AI_ARCHITECTURE.md §38.3) runs on every AI change: capture, evaluate, analyze, improve, validate.
- Metrics baseline captured at launch; regression gate protects it.

---

## 29. Testing Workflow

Testing is a continuous workflow, not a phase at the end (TESTING_STRATEGY.md §1.2, §28).

| Stage | What happens |
| ----- | ------------ |
| **Development testing** | Unit and targeted integration tests written with the code; run on every push. |
| **Integration testing** | Full integration + API contract suites on every PR and merge. |
| **Regression testing** | Full regression on merges and release candidates (TESTING_STRATEGY.md §20). |
| **Acceptance testing** | Internal acceptance per feature; UAT with students at release (TESTING_STRATEGY.md §22). |
| **Release testing** | Smoke, performance, security, and AI evaluation on release candidates (TESTING_STRATEGY.md §21, §31). |

**Rules:**
- Tests are part of the Definition of Done (Section 34; BACKEND_ARCHITECTURE.md §26).
- External LLM calls are mocked or gated in CI (BACKEND_ARCHITECTURE.md §26).
- Every fix is protected by a regression test (TESTING_STRATEGY.md §20.1).

---

## 30. Deployment Workflow

Deployment follows a controlled sequence (TESTING_STRATEGY.md §21, §27). It is validated at every step.

### 30.1 Build

- Images are built from versioned source with multi-stage, slim, non-root production images (BACKEND_ARCHITECTURE.md §27).
- Build succeeds cleanly with no type errors or warnings (TESTING_STRATEGY.md §31.1).

### 30.2 Validation

- CI validates the build: full fast suite, contract, smoke (TESTING_STRATEGY.md §21.2).
- Staging validates the candidate in a production-like topology.

### 30.3 Deployment

- Deployment is scripted and repeatable; the target environment is explicitly configured (Section 16).
- Deployments are additive and versioned; migration order follows DATABASE_DESIGN.md §28.

### 30.4 Health Check

- Post-deployment smoke verifies health, database, vector store, and LLM gateway reachability (TESTING_STRATEGY.md §21.3; AI_ARCHITECTURE.md §31.1).

### 30.5 Rollback

- A failed post-deploy check triggers the documented rollback path (Section 22.5).

### 30.6 Monitoring

- Post-deploy monitoring tracks health, errors, latency, and AI metrics (TESTING_STRATEGY.md §26).
- Alerts feed the maintenance loop (Section 3.6).

---

## 31. Risk Management

Risks are identified, owned, and mitigated throughout development (TESTING_STRATEGY.md §33).

| Category | Key risks | Mitigation |
| -------- | --------- | ---------- |
| **Technical** | Flaky tests, coverage gaps, environment drift, E2E fragility | Deterministic isolated tests; coverage gates; reproducible environments; pyramid guidance (TESTING_STRATEGY.md §33.1). |
| **AI** | Hallucination, model/prompt drift, embedding change, nondeterminism | Grounding rules, golden eval harness, golden retrieval sets, mocked LLM in CI (TESTING_STRATEGY.md §33.2). |
| **Security** | Prompt injection, data leakage, secret exposure | Guardrails, owner-scoping tests, RBAC matrix, log-safety rules, CI secret scan (Section 26). |
| **Performance** | Load degradation, AI latency creep, DB slowdown | Load/stress testing, latency monitoring, index validation (TESTING_STRATEGY.md §33.5). |
| **Project** | Scope creep, milestone slip, supervisor misalignment, single-owner bus factor | Phase discipline, milestone reviews, documentation, shared knowledge (Sections 4–5, 25). |

**Process:** Risks are reviewed each cycle; new risks are added, and mitigations are tracked to closure.

---

## 32. Quality Gates

Quality gates are the checkpoints that must pass before work progresses. They enforce the Definition of Done (Section 34) and the release criteria (TESTING_STRATEGY.md §31).

| Gate | Applies before | Check |
| ---- | -------------- | ----- |
| **Architecture review** | Implementation of a new feature | Design derived from the source docs; no architecture deviation. |
| **Code review** | Merge to `develop`/`main` | Section 12 criteria pass. |
| **Testing pass** | Merge / release | All relevant suites green (TESTING_STRATEGY.md §31.2). |
| **Documentation complete** | Merge / release | Docs updated with the change (Section 18). |
| **Performance validation** | Release candidate | Budgets met, no regressions (TESTING_STRATEGY.md §31.3). |
| **Security validation** | Release candidate | Security checks pass; no unresolved high findings (TESTING_STRATEGY.md §31.4). |

**Rules:**
- Gates are enforced by CI where automated; by the reviewer and release process where manual.
- A gate failure blocks progress until resolved — never bypassed silently.

---

## 33. Definition of Ready

A task is **Ready to Start** only when all of the following hold (TESTING_STRATEGY.md §22.1 supports acceptance-based readiness).

| Criterion | Meaning |
| --------- | ------- |
| **Requirements complete** | What to build is clear and within Phase 1 scope. |
| **Design approved** | The change is derived from the relevant architecture doc; design review passed if required. |
| **Dependencies available** | Required services, data, keys (e.g., Gemini API key, seed data) are available to the task. |
| **Acceptance criteria defined** | Testable criteria exist to verify the task (fed by the requirements). |

**Rule:** Work does not begin on a task that is not Ready. This keeps flow predictable and avoids rework.

---

## 34. Definition of Done

A task is **Done** only when all of the following hold (PROJECT_RULES.md Definition of Done; BACKEND_ARCHITECTURE.md §26; TESTING_STRATEGY.md §31).

| Criterion | Meaning |
| --------- | ------- |
| **Code complete** | Implemented per the architecture docs, coding standards, and folder rules. |
| **Tests passed** | Relevant automated suites pass; the feature is covered (TESTING_STRATEGY.md §29). |
| **Documentation updated** | The relevant docs/API/README updated in the same change (Section 18). |
| **Review approved** | Code review passed (Section 12); PR merged. |
| **Performance verified** | No perf regressions; budgets respected where applicable (Section 27). |
| **Security verified** | No new security issues; validation at boundaries (Section 26). |

**Rule:** Done is verified, not assumed. A feature that meets code but not the rest is not done.

---

## 35. Development Best Practices

The day-to-day practices that keep the project healthy (PROJECT_RULES.md Development Rules, Coding Standards).

| Practice | Rule |
| -------- | ---- |
| **Keep components small** | One responsibility per component/service/module. |
| **Avoid duplication** | Reuse before writing; extract shared parts (PROJECT_RULES.md Development Rules). |
| **Follow architecture** | Code derives from the source docs; no layer-skipping. |
| **Write clean code** | Clear names, small functions, readable structure. |
| **Keep functions focused** | One function does one thing; easy to test in isolation. |
| **Use shared components** | Build new UI from the shared library only (ui-ux-design.md §25). |
| **Maintain type safety** | Strict TypeScript, strict Python typing — no `any`, no untyped boundaries. |

---

## 36. Future Development Roadmap

Future improvements extend the platform beyond Phase 1 (PROJECT_RULES.md Future Scope, AI Development Roadmap). They are placeholders until the corresponding phases begin.

| Capability | Phase | Notes |
| ---------- | ----- | ----- |
| **Admin Panel** | Future | Administrative management dashboard (PROJECT_RULES.md UI Pages). |
| **Live notifications** | Future | WebSockets for real-time notifications and live agent status (API_SPECIFICATION.md §39). |
| **Streaming responses** | Future | SSE/token streaming with the completed-response envelope (API_SPECIFICATION.md §39). |
| **Analytics** | Future | Usage analytics from monitoring data (AI_ARCHITECTURE.md §31.6). |
| **Mobile app** | Future | Same versioned REST surface; no separate mobile API (API_SPECIFICATION.md §39). |
| **Additional AI agents** | Future | Registration, Finance, Scholarship, Library, Hostel, IT Support (PROJECT_RULES.md AI Development Roadmap). |
| **Advanced search** | Future | Re-ranking, metadata-rich retrieval, hybrid search. |
| **Multi-language support** | Future | Multilingual UI and assistant (PROJECT_RULES.md AI Development Roadmap). |
| **Cloud deployment** | Future | Managed PostgreSQL/pgvector, Redis caching, horizontal scaling (BACKEND_ARCHITECTURE.md §23). |

**Roadmap rules:**
- Future items are not built in Phase 1; only placeholders exist (PROJECT_RULES.md).
- Each future item is planned through this workflow: research → design → phases → tests → release.
- Future capabilities extend existing contracts additively and versioned (API_SPECIFICATION.md §39).

---

## Important

This document is the **permanent development workflow guide** and the **single source of truth for the complete software development lifecycle** of the project.

It must be read together with:

- **PROJECT_RULES.md** — master project rules (principles, phases, Git, coding, DoD).
- **docs/architecture/ui-ux-design.md** — the only design source for the frontend.
- **docs/architecture/BACKEND_ARCHITECTURE.md** — layered architecture and backend standards.
- **docs/architecture/DATABASE_DESIGN.md** — schema, migrations, transactions, and retention.
- **docs/architecture/AI_ARCHITECTURE.md** — agents, RAG, prompts, and evaluation.
- **docs/architecture/API_SPECIFICATION.md** — endpoint contracts and API standards.
- **docs/architecture/TESTING_STRATEGY.md** — the complete testing strategy and quality gates.

All development activity — planning, coding, review, testing, release, and maintenance — must be derived from this document. Any workflow that deviates from these standards must be corrected before it is accepted.

**This document is architecture and documentation only.** It contains no implementation code, no Python, no SQL, no Docker configuration, no Git commands, and no scripts. Implementation is derived from these standards, following the project's Development Rules and Definition of Done.

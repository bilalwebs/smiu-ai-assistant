# DEPLOYMENT.md

**Agentic AI-Based University Workflow Automation System**
Multi-Agent Student Support Platform — developed for **Sindh Madressatul Islam University (SMIU)**

> Version: 1.0 · Status: Approved Architecture · Last Updated: August 2026 · Owner: Final Year Project Team
> Scope: Single source of truth for the complete deployment architecture and operational strategy — infrastructure, environments, Docker, reverse proxy, security, monitoring, backup, recovery, and production readiness.
> Sufficiently detailed that the entire deployment and operations layer can be derived without additional deployment instructions.
> This document is **architecture and documentation only** — it contains no Dockerfiles, no compose files, no Nginx configuration, no shell scripts, no CI/CD YAML, no Python, and no SQL.

---

## Table of Contents

1. [Deployment Philosophy](#1-deployment-philosophy)
2. [Deployment Objectives](#2-deployment-objectives)
3. [Deployment Architecture Overview](#3-deployment-architecture-overview)
4. [Deployment Environments](#4-deployment-environments)
5. [Infrastructure Architecture](#5-infrastructure-architecture)
6. [Docker Strategy](#6-docker-strategy)
7. [Docker Compose Architecture](#7-docker-compose-architecture)
8. [Frontend Deployment](#8-frontend-deployment)
9. [Backend Deployment](#9-backend-deployment)
10. [Database Deployment](#10-database-deployment)
11. [AI Services Deployment](#11-ai-services-deployment)
12. [Environment Variables](#12-environment-variables)
13. [Secrets Management](#13-secrets-management)
14. [Reverse Proxy](#14-reverse-proxy)
15. [HTTPS & SSL](#15-https--ssl)
16. [Domain Strategy](#16-domain-strategy)
17. [File Storage Strategy](#17-file-storage-strategy)
18. [Logging Strategy](#18-logging-strategy)
19. [Monitoring Strategy](#19-monitoring-strategy)
20. [Health Check Strategy](#20-health-check-strategy)
21. [Backup Strategy](#21-backup-strategy)
22. [Restore Strategy](#22-restore-strategy)
23. [Disaster Recovery Plan](#23-disaster-recovery-plan)
24. [Security Strategy](#24-security-strategy)
25. [Performance Optimization](#25-performance-optimization)
26. [Scalability Strategy](#26-scalability-strategy)
27. [Load Balancing](#27-load-balancing)
28. [Deployment Workflow](#28-deployment-workflow)
29. [Release Management](#29-release-management)
30. [Rollback Strategy](#30-rollback-strategy)
31. [Maintenance Strategy](#31-maintenance-strategy)
32. [Operational Checklist](#32-operational-checklist)
33. [Production Readiness Checklist](#33-production-readiness-checklist)
34. [Future Deployment Improvements](#34-future-deployment-improvements)

---

## 1. Deployment Philosophy

The deployment philosophy is the permanent set of operational principles governing how the platform is shipped, run, and maintained. It derives from the deployment readiness design in **BACKEND_ARCHITECTURE.md** (§27), the release and deployment workflow in **DEVELOPMENT_WORKFLOW.md** (§22, §30), and the operational requirements of **TESTING_STRATEGY.md** (§21, §27).

### 1.1 Production First

| Principle | Meaning |
| --------- | ------- |
| **Deployable from day one** | Every module is production-ready from the start (BACKEND_ARCHITECTURE.md §1.4) — no "works locally" exceptions. |
| **Production-like staging** | Staging mirrors production topology so release validation is meaningful (TESTING_STRATEGY.md §27). |
| **No environment drift** | The same artifact is promoted through environments; configuration is the only difference (Section 4). |

### 1.2 Reliability

- Deployments are repeatable, scripted, and validated — never ad-hoc (DEVELOPMENT_WORKFLOW.md §30).
- Every deploy is health-checked and monitored; failures trigger the documented rollback (Sections 20, 30).
- The system fails gracefully at the operational layer: degraded states are detected, surfaced, and recoverable (AI_ARCHITECTURE.md §31.1).

### 1.3 Scalability

- The API is **stateless** — any number of instances can serve traffic; sessions and state live in the database (BACKEND_ARCHITECTURE.md §23).
- Infrastructure is designed to scale horizontally before vertically (Section 26).
- Scaling is additive and versioned — never a redesign.

### 1.4 Security

- Secure by default: HTTPS, least privilege, secrets never in code, encrypted data at rest and in transit (Section 24).
- Environment variables hold all secrets; `.env.example` is the template (PROJECT_RULES.md Environment Variables).
- Security is validated before every release (TESTING_STRATEGY.md §31.4).

### 1.5 Maintainability

- Infrastructure is documented, versioned, and owned — someone can operate it without tribal knowledge.
- Logging, monitoring, and backup are standard parts of every deployment (Sections 18–21).
- Configuration is centralized and environment-aware (DEVELOPMENT_WORKFLOW.md §17).

### 1.6 High Availability

- The design targets no single point of failure within the application layer (stateless nodes).
- Database and AI dependencies are monitored for availability (AI_ARCHITECTURE.md §31.5).
- Full multi-instance/multi-region high availability is a future enhancement (Section 34).

### 1.7 Disaster Recovery

- Every asset has a documented backup and restore path (Sections 21–22).
- Recovery objectives (RPO/RTO) are defined per DATABASE_DESIGN.md §29 (Section 23.5).
- Restore drills are part of the Definition of Done for any schema or infrastructure change (DATABASE_DESIGN.md §29).

---

## 2. Deployment Objectives

The objectives below define what successful deployment and operation means. Every operational activity maps to at least one objective.

| Objective | Measure of success |
| --------- | ------------------ |
| **Stability** | Deployments are repeatable; releases do not break running systems; rollback is always available. |
| **Security** | All traffic encrypted; no secrets exposed; secure headers and least-privilege roles enforced (Section 24). |
| **Performance** | Response-time budgets met in production (API_SPECIFICATION.md §36.1; AI_ARCHITECTURE.md §31.2). |
| **Availability** | Health, error, and AI availability metrics within thresholds (AI_ARCHITECTURE.md §38.1). |
| **Ease of maintenance** | Logging, monitoring, and backup make operations routine and documented (Sections 18–21). |
| **Scalability** | Capacity grows by adding instances/roles without architectural change (Section 26). |

---

## 3. Deployment Architecture Overview

The deployed system consists of the following cooperating parts, orchestrated by Docker Compose (PROJECT_RULES.md Tech Stack — Docker, Docker Compose). The reverse proxy is the single public entry point.

### 3.1 Frontend

- Next.js 15 application (React 19, TypeScript, Tailwind CSS, shadcn/ui).
- Deployed as a containerized production build serving the server-rendered app and static assets (Section 8).
- Public pages and the Student Portal (login, dashboard, AI chat, history) served through the reverse proxy (Section 14).

### 3.2 Backend

- FastAPI REST API exposing `/api/v1` per API_SPECIFICATION.md.
- Contains the layered architecture: routers → services → repositories → database (BACKEND_ARCHITECTURE.md §6).
- Hosts background workers for long operations (embeddings, indexing, notifications) (BACKEND_ARCHITECTURE.md §19).
- Serves the health-check endpoints used by orchestration (Section 20).

### 3.3 Database

- PostgreSQL (production), SQLite (local development) per PROJECT_RULES.md Tech Stack.
- Persists all 16 tables per DATABASE_DESIGN.md (§12–25).
- Persistent storage with backups integrated (Section 10, 21).

### 3.4 AI Services

- LangGraph workflow (Coordinator + Admission + Examination + FAQ agents) and LangChain RAG pipeline (AI_ARCHITECTURE.md §11, §14).
- Gemini 2.5 Flash as the primary LLM — an external service reached over HTTPS (Section 11).
- Sentence Transformers for embeddings (local model execution) (AI_ARCHITECTURE.md §16.1).
- FAISS vector store for retrieval — in-memory index over a persisted index file (Section 11).

### 3.5 Knowledge Base

- Source documents under `knowledge/` (admission, examination, faq, documents) (PROJECT_RULES.md Knowledge Base Structure).
- Chunk metadata persisted in `knowledge_documents`/`knowledge_chunks`; vectors in the FAISS index (DATABASE_DESIGN.md §21).
- The index is regenerable from source — treated as derived data (DATABASE_DESIGN.md §35).

### 3.6 Reverse Proxy

- Nginx as the single public entry point (Section 14).
- Routes HTTPS traffic, serves static assets, proxies the API, enforces security headers, and terminates TLS.

### 3.7 Static Assets

- Next.js static assets (JS/CSS/images) served by the frontend container and, at scale, a CDN (Section 34).
- Uploaded documents stored on a persistent volume (Section 17).

### 3.8 External Services

- Gemini 2.5 Flash API (LLM) — external, key-authenticated.
- Email dispatch for verification/reset notifications — external, key-authenticated.
- These are the only external dependencies; all failures degrade gracefully (BACKEND_ARCHITECTURE.md §24).

---

## 4. Deployment Environments

Five environments exist, each with an isolated purpose and configuration (DEVELOPMENT_WORKFLOW.md §16; TESTING_STRATEGY.md §27).

| Environment | Purpose | Database | AI |
| ----------- | ------- | -------- | -- |
| **Local Development** | Day-to-day development on a developer machine. | SQLite | Mocked/gated by default; optional real LLM. |
| **Development** | Shared team development environment (compose stack). | SQLite or dev PostgreSQL | Mocked LLM. |
| **Testing** | Automated test suites run in CI. | Dedicated test DB (PostgreSQL) | Mocked LLM; golden fixtures. |
| **Staging** | UAT, E2E, performance, and release-candidate validation. | PostgreSQL with realistic seeded data (no real PII) | Real Gemini 2.5 Flash permitted with monitoring. |
| **Production** | Live service for SMIU students. | PostgreSQL | Real LLM; full guardrails and monitoring. |

**Isolation rules:**
- Environments never share databases, credentials, or secrets (TESTING_STRATEGY.md §27.5).
- Automated tests never run against production data or services (TESTING_STRATEGY.md §27.4).
- Staging mirrors production topology so validation is meaningful (Section 1.1).
- `ENVIRONMENT` variable selects the configuration scope (BACKEND_ARCHITECTURE.md §27).

---

## 5. Infrastructure Architecture

The infrastructure consists of the following logical components, each with a clear responsibility.

### 5.1 Application Server

- Runs the FastAPI backend container(s) (Section 9).
- Stateless — horizontal scaling adds instances without changing state ownership (BACKEND_ARCHITECTURE.md §23).

### 5.2 Database Server

- Runs PostgreSQL with persistent storage (Section 10).
- Owns all transactional data; never co-located with ephemeral application state.

### 5.3 AI Components

- The AI service (LangGraph/LangChain) runs inside the backend or as a separate AI service container (BACKEND_ARCHITECTURE.md §20).
- Sentence Transformers run locally; Gemini is external (Section 11).
- AI availability and latency are monitored (AI_ARCHITECTURE.md §31).

### 5.4 Vector Store

- FAISS index loaded in memory per instance; persisted to a shared volume for rebuild and recovery (AI_ARCHITECTURE.md §16.1).
- Regenerable from `knowledge/` + chunk metadata (DATABASE_DESIGN.md §21).

### 5.5 Static File Storage

- Persistent volume for uploaded documents and generated assets (Section 17).
- Backed up with the rest of the data (Section 21).

### 5.6 Reverse Proxy

- Nginx terminates TLS and routes traffic (Section 14).
- Serves static assets, proxies `/api/v1`, and enforces security headers.

---

## 6. Docker Strategy

Containerization follows the Docker deployment readiness in BACKEND_ARCHITECTURE.md §27 and the containerization purpose in PROJECT_RULES.md.

### 6.1 Containerization Philosophy

- **One responsibility per container** — frontend, backend, database each run in their own container with a clear role.
- **Reproducibility** — the same image builds the same runtime everywhere.
- **Production-first images** — multi-stage builds, slim production images, non-root runtime (BACKEND_ARCHITECTURE.md §27).
- **No state in containers** — all persistent state lives in volumes or the database; containers are ephemeral.

### 6.2 Service Separation

| Service | Responsibility |
| ------- | -------------- |
| **Frontend** | Next.js production server and static assets. |
| **Backend/API** | FastAPI REST API and AI orchestration. |
| **Backend worker** | Background jobs (embeddings, indexing, notifications, retention) — separated from the request path (BACKEND_ARCHITECTURE.md §19). |
| **Database** | PostgreSQL. |
| **Reverse proxy** | Nginx entry point (Section 14). |

### 6.3 Container Responsibilities

- Containers run a single process (or a well-defined process group); no multi-service containers.
- Each container depends on documented services and fails fast when dependencies are missing.
- Non-root execution, read-only filesystems where feasible, and no unnecessary tools in images (security, Section 24).

### 6.4 Image Versioning

- Images are tagged with the release version (SemVer, DEVELOPMENT_WORKFLOW.md §23) plus a unique build identifier.
- `latest` is never deployed blindly — deployments pin exact immutable tags.
- Image provenance: built from versioned source in a controlled pipeline (Section 28).

### 6.5 Volume Strategy

- Persistent volumes for: PostgreSQL data, uploaded documents, the FAISS index (persisted copy), and backup staging.
- Ephemeral volumes (or none) for caches and temporary files.
- Volume backups integrated with the backup strategy (Section 21).

### 6.6 Network Strategy

- Internal Docker network isolates services; only the reverse proxy is exposed publicly.
- The backend reaches the database and AI services only over the internal network.
- External egress is limited to the LLM and email providers.

---

## 7. Docker Compose Architecture

Docker Compose orchestrates the local/development and staging stacks (PROJECT_RULES.md — Local and production orchestration). This section defines the *design* — the compose file itself is derived from it.

### 7.1 Service Organization

- Services are organized by role: proxy, frontend, backend, worker, database.
- Each service declares its image, environment scope, networks, volumes, and dependencies.

### 7.2 Dependencies

- The backend depends on the database; the frontend depends on the backend; the proxy depends on both.
- Dependencies are declared explicitly so orchestration starts services in a sensible order.

### 7.3 Startup Order

- The database starts first; migrations run as a **separate step** before the backend serves traffic (BACKEND_ARCHITECTURE.md §27; DATABASE_DESIGN.md §28).
- The worker starts after the database and schema are ready.
- The proxy starts after frontend and backend are healthy (readiness, Section 20).

### 7.4 Health Checks

- Every service declares a health check tied to its readiness contract (Section 20).
- The reverse proxy routes only to healthy instances; unhealthy services are surfaced and excluded.
- Health-check status feeds orchestration decisions and monitoring (Section 19).

### 7.5 Networking

- An internal bridge network carries service-to-service traffic.
- Only the proxy publishes ports to the host/public interface.
- Database ports are never exposed publicly.

### 7.6 Persistent Volumes

- Named volumes back PostgreSQL data, uploads, and the index copy.
- Volumes are never destroyed on container recreation (state survives rebuilds).
- Backup jobs target these volumes (Section 21).

---

## 8. Frontend Deployment

Frontend deployment follows the Next.js 15 app and the design decisions in ui-ux-design.md (which is the only design source).

### 8.1 Next.js

- Deployed as a production build serving the server-rendered application (App Router, ui-ux-design.md §39).
- The container runs the optimized production server — not the development server.

### 8.2 Static Assets

- Static assets (JS/CSS/images/fonts) are built and served efficiently; a CDN can front them at scale (Section 34).
- Assets are content-hashed by the build for cache correctness.

### 8.3 Image Optimization

- Next.js image optimization configured per the performance budget (ui-ux-design.md §32).
- Lazy loading and code splitting honored (PROJECT_RULES.md Performance & Security).

### 8.4 Environment Variables

- Frontend runtime configuration is provided at deploy time via environment (Section 12).
- No secrets are embedded in the client bundle (PROJECT_RULES.md Environment Variables).
- Public API base URL is environment-scoped (dev/staging/production).

### 8.5 Production Build

- The production build must pass with no type errors or warnings (PROJECT_RULES.md Definition of Done).
- The build is validated in CI before promotion (TESTING_STRATEGY.md §31.1; DEVELOPMENT_WORKFLOW.md §30.2).

---

## 9. Backend Deployment

Backend deployment follows the layered backend architecture (BACKEND_ARCHITECTURE.md) and the API specification (API_SPECIFICATION.md).

### 9.1 FastAPI

- Deployed as a production ASGI application serving the REST API under `/api/v1`.
- Production logging at `INFO` level; structured, correlation-tagged, JSON output (BACKEND_ARCHITECTURE.md §27).

### 9.2 API Services

- The API is stateless — any instance can serve any request; sessions and state live in the database (BACKEND_ARCHITECTURE.md §23).
- Multiple instances can be started behind the reverse proxy for capacity (Section 26).

### 9.3 Workers

- Background workers run jobs off the request path: embeddings, indexing, notifications, retention (BACKEND_ARCHITECTURE.md §19).
- Workers are scaled independently of the API (Section 26.1).

### 9.4 Background Tasks

- Long operations (re-index, upload processing) run as background jobs — never synchronous (API_SPECIFICATION.md §36.2).
- Job queues are retried and monitored; failures are surfaced and recoverable (DATABASE_DESIGN.md §34.4).

### 9.5 Configuration

- All runtime configuration is environment-driven (Sections 12–13).
- Migrations are a separate deploy step; the API never auto-migrates on boot (BACKEND_ARCHITECTURE.md §27).

---

## 10. Database Deployment

Database deployment follows the schema, migration, and backup design in DATABASE_DESIGN.md.

### 10.1 PostgreSQL Deployment

- PostgreSQL runs in a dedicated container with persistent storage (Section 7.6).
- Schema is created and evolved by Alembic migrations applied as a controlled step (DATABASE_DESIGN.md §28).

### 10.2 Persistent Storage

- Database data lives on a named persistent volume (or managed disk in the future).
- Storage is backed up per the backup strategy (Section 21) and never wiped by redeploys.

### 10.3 Database Security

- The application connects with a dedicated least-privilege role (DML + sequence usage on `public`); migrations use a separate elevated role at deploy time (DATABASE_DESIGN.md §30.1).
- No superuser access from the application; no exposed database ports (Section 7.5).
- Backups encrypted at rest; access restricted (DATABASE_DESIGN.md §29).

### 10.4 Database Connections

- Connection pooling sized per instance; bounded to avoid exhaustion (BACKEND_ARCHITECTURE.md §23).
- Pool behavior validated under load (TESTING_STRATEGY.md §16.6).

### 10.5 Backup Integration

- Backups executed by a dedicated scheduled job per the strategy in DATABASE_DESIGN.md §29 (Section 21).
- Restore drills are scheduled and validated (Section 22).

---

## 11. AI Services Deployment

AI services deployment follows the AI architecture (AI_ARCHITECTURE.md) and the RAG integration design (BACKEND_ARCHITECTURE.md §21).

### 11.1 LangGraph

- The LangGraph workflow (Coordinator + specialists) runs inside the AI service (AI_ARCHITECTURE.md §11).
- The workflow is stateless at runtime — state is rebuilt from persistence (AI_ARCHITECTURE.md §21.4).

### 11.2 LangChain

- Retrieval chains and RAG orchestration run within the AI service (PROJECT_RULES.md Tech Stack).
- Retrieval precedes every LLM generation (grounding rule, PROJECT_RULES.md AI Behaviour Rules).

### 11.3 Gemini Integration

- Gemini 2.5 Flash is an external service reached over HTTPS with an API key (Section 12).
- Calls are bounded by timeouts; failures map to typed errors and graceful fallback (BACKEND_ARCHITECTURE.md §24).
- Rate limits and quota are monitored (AI_ARCHITECTURE.md §31.3).

### 11.4 Embedding Models

- Sentence Transformers run locally inside the AI service (AI_ARCHITECTURE.md §16.1).
- The model is loaded lazily to keep startup fast (BACKEND_ARCHITECTURE.md §23).

### 11.5 FAISS

- The FAISS index is loaded in memory per instance for low-latency search (AI_ARCHITECTURE.md §16.1, §32.2).
- A persisted copy of the index sits on a shared volume for rebuild and recovery (Section 5.4).
- Missing/corrupt index is detected by readiness checks and regenerated (AI_ARCHITECTURE.md §31.1).

### 11.6 Knowledge Base

- Source documents under `knowledge/` are packaged with the release (versioned in the repo).
- Re-indexing is a background job; the index is regenerable from source (DATABASE_DESIGN.md §35).

---

## 12. Environment Variables

All configuration and secrets are supplied through environment variables (PROJECT_RULES.md Environment Variables; BACKEND_ARCHITECTURE.md §7). Actual values are never documented or committed.

| Variable group | Variables | Notes |
| -------------- | --------- | ----- |
| **API keys** | `GEMINI_API_KEY`, email provider keys | Secret; from the secret store, never committed or logged. |
| **Database credentials** | `DATABASE_URL` (and split user/password/host where used) | Secret; environment-specific; least-privilege roles (DATABASE_DESIGN.md §30.1). |
| **JWT secrets** | `JWT_SECRET`, refresh-secret material | Secret; strong, rotated (Section 13.2). |
| **AI configuration** | Model name, temperature, `CHAT_HISTORY_LIMIT`, `RAG_TOP_K`, thresholds | Non-secret; environment-tunable (DEVELOPMENT_WORKFLOW.md §17). |
| **Application configuration** | `ENVIRONMENT`, CORS allow-list, log level, API base URLs, pagination defaults, rate limits | Non-secret; environment-scoped. |
| **Storage/secrets misc** | `SECRET_KEY`, `FAISS_PATH` | `SECRET_KEY` secret; paths environment-specific. |

**Rules:**
- `.env.example` is the single committed template; real `.env` files are gitignored (PROJECT_RULES.md).
- Never log environment variables or their values (PROJECT_RULES.md Logging & Monitoring).
- Never expose values through health/version endpoints (API_SPECIFICATION.md §24 — non-sensitive metadata only).

---

## 13. Secrets Management

### 13.1 Secret Storage

- Secrets live in a secret manager / encrypted environment at deploy time — never in the repository or images.
- For the FYP scope, secrets are injected from a protected environment (CI secret store, deploy host secret file) and referenced by name only.
- `.env.example` documents names, never values (PROJECT_RULES.md).

### 13.2 Rotation Policy

- JWT and app secrets are rotated on a schedule and immediately if exposure is suspected.
- Rotation is coordinated with session invalidation (sessions in the DB, DATABASE_DESIGN.md §25).
- API keys follow the provider's rotation guidance; rotation is rehearsed.

### 13.3 Access Control

- Only authorized operators and the deployment pipeline hold production secrets.
- Least privilege: services receive only the secrets they need (DATABASE_DESIGN.md §30.1).
- Access is reviewed; revoked access never lingers.

### 13.4 Secure Distribution

- Secrets travel over encrypted channels only — never in chat, email, or unencrypted logs.
- CI injects secrets at job runtime; they are never written into build artifacts.
- Backup files never contain plaintext secrets (DATABASE_DESIGN.md §29).

---

## 14. Reverse Proxy

Nginx is the single public entry point (Section 3.6). This section defines its operational role; configuration is derived from it.

### 14.1 Nginx Role

- Terminates TLS (Section 15) and routes all external traffic.
- Serves as the single externally reachable component; all other services are internal (Section 7.5).

### 14.2 HTTPS Routing

- All traffic is HTTPS; HTTP redirects to HTTPS (Section 15.2).
- Only the public frontend path and `/api/v1` are routed externally.

### 14.3 Static File Serving

- Static assets are served efficiently with correct caching headers (Section 8.2).
- The proxy fronting a CDN is a future enhancement (Section 34).

### 14.4 API Routing

- `/api/v1/*` routes to the backend service.
- `/health*` routes to the backend health endpoints (Section 20) for orchestration.
- Unknown paths never leak internal service details.

### 14.5 Security Headers

- CSP, frame/cache protections, and related headers enforced at the proxy (BACKEND_ARCHITECTURE.md §22).
- Headers verified by security checks before release (TESTING_STRATEGY.md §31.4).

---

## 15. HTTPS & SSL

### 15.1 SSL Certificates

- TLS certificates are obtained and managed for the production domain(s) (Section 16).
- Certificates are valid, trusted, and enforced at the reverse proxy.

### 15.2 HTTPS Enforcement

- All external traffic is HTTPS; plaintext HTTP redirects to HTTPS.
- Cookies for auth are secure-only; the app never transmits tokens over HTTP (API_SPECIFICATION.md §5).

### 15.3 Certificate Renewal

- Renewal is automated (Let's Encrypt-style) with monitoring for imminent expiry.
- Renewal failures alert operators before expiry affects the service.

### 15.4 Secure Communication

- HTTPS everywhere: browser ↔ proxy, proxy ↔ services (internal TLS where feasible), service ↔ external providers (Gemini, email).
- Database connections are encrypted where the provider allows (Section 10.3).

---

## 16. Domain Strategy

Domains are planned for clarity and future growth. Exact values are deployment decisions; the strategy is defined here.

| Target | Strategy |
| ------ | -------- |
| **Frontend domain** | Primary domain (e.g., `app.` / `www.` style) serving the Next.js app. |
| **Backend API domain** | Separate subdomain or path-relative routing under the primary domain for `/api/v1`. |
| **Future admin domain** | A reserved subdomain (e.g., `admin.`) for the future admin panel (PROJECT_RULES.md UI Pages; API_SPECIFICATION.md §25). |
| **Subdomain planning** | Subdomains reserved up front (api, admin, and future assets/analytics) so adding them never forces a redirect/rebrand. |

**Rules:**
- All domains serve over HTTPS (Section 15).
- CORS allow-list matches the frontend domain(s) exactly (BACKEND_ARCHITECTURE.md §22).

---

## 17. File Storage Strategy

File storage handles user-uploaded and generated content per BACKEND_ARCHITECTURE.md §18 and API_SPECIFICATION.md §35.

| Content | Storage | Notes |
| ------- | ------- | ----- |
| **Uploaded documents** | Persistent volume | UUID-based safe filenames; SHA-256 checksums (API_SPECIFICATION.md §35; DATABASE_DESIGN.md §20). |
| **Static files** | Frontend container/volume; CDN at scale | Content-hashed for cache correctness. |
| **Generated reports** | Persistent volume | Backed up; retention per policy. |
| **Temporary files** | Ephemeral storage | Never persisted; cleaned up after processing. |
| **Backup storage** | Encrypted, off-box volume/object store | Separate from live data (DATABASE_DESIGN.md §29). |

**Rules:**
- Uploads are validated (type, size, checksum) before storage (API_SPECIFICATION.md §35).
- File metadata lives in the database (`documents`, DATABASE_DESIGN.md §20); the volume is the blob store.
- All persistent storage is covered by the backup strategy (Section 21).

---

## 18. Logging Strategy

Logging follows PROJECT_RULES.md Logging & Monitoring, BACKEND_ARCHITECTURE.md §16, and AI_ARCHITECTURE.md §30.

| Log type | Captures | Destination |
| -------- | -------- | ----------- |
| **Application logs** | Backend service behavior, request lifecycle, correlation IDs | Structured app logs (JSON) |
| **API logs** | Method, path, status, duration, user id (when available) (API_SPECIFICATION.md §37) | Structured app logs |
| **AI logs** | Model, tokens, latency, routing, retrieval scores, guardrail events (AI_ARCHITECTURE.md §30.1) | Structured app logs + `agent_logs` |
| **Database logs** | Slow queries, connection issues, lock waits (DATABASE_DESIGN.md §31) | Database logs |
| **Access logs** | Reverse-proxy request/response metadata | Proxy logs |
| **Error logs** | Exceptions, retries, fallbacks, timeouts | Structured error logs |

**Rules:**
- Never log secrets, API keys, tokens, passwords, or raw PII (PROJECT_RULES.md).
- Logs carry correlation IDs for cross-service tracing (API_SPECIFICATION.md §37).
- Logs are aggregated and searchable in production (Section 19.2).
- Retention follows DATABASE_DESIGN.md §35 for the DB-side audit/agent logs.

---

## 19. Monitoring Strategy

Monitoring follows AI_ARCHITECTURE.md §31 and API_SPECIFICATION.md §37, extended to the whole platform.

### 19.1 Server Monitoring

- CPU, memory, disk, and network utilization per host/container.
- Alerts on resource exhaustion before it degrades the service.

### 19.2 Application Monitoring

- Request rates, error rates, latency percentiles (p50/p95/p99), and availability per endpoint.
- Log aggregation and search for debugging (Section 25 in TESTING_STRATEGY.md).

### 19.3 Database Monitoring

- Connection-pool usage, slow queries, lock waits, and replication health (DATABASE_DESIGN.md §31).
- Backup success/failure monitoring (Section 21).

### 19.4 AI Monitoring

- Routing distribution, per-agent latency/error rate, token usage, TTFT (AI_ARCHITECTURE.md §31.2–31.4).
- AI availability and fallback rate (AI_ARCHITECTURE.md §31.5).

### 19.5 Performance Monitoring

- Latency budgets tracked continuously (API_SPECIFICATION.md §36.1).
- Degradation alerts feed the maintenance loop (Section 31).

### 19.6 Health Monitoring

- Health endpoints polled continuously (Section 20); degraded states alert operators (AI_ARCHITECTURE.md §31.1).

---

## 20. Health Check Strategy

Health checks follow the health-check API design in API_SPECIFICATION.md §24 and the orchestration readiness in BACKEND_ARCHITECTURE.md §27.

### 20.1 Application Health

- The application process reports liveness and readiness separately.

### 20.2 Database Health

- Readiness fails if the database is unreachable; the database container has its own health probe.

### 20.3 AI Health

- Readiness fails if the vector store or AI gateway is unreachable (AI_ARCHITECTURE.md §31.1).

### 20.4 API Health

- `GET /health/live` — process alive (always 200 while running).
- `GET /health/ready` — dependencies reachable (database, FAISS, AI gateway); 503 otherwise (API_SPECIFICATION.md §24).
- `GET /health` — combined summary.
- `GET /health/version` — non-sensitive version/build metadata (API_SPECIFICATION.md §24).

### 20.5 Readiness Checks

- Readiness gates traffic: the reverse proxy routes only to ready instances (Section 7.4).
- Used by orchestration to sequence startups and scale-ins.

### 20.6 Liveness Checks

- Liveness gates restarts: a dead process is restarted automatically.
- Liveness and readiness are kept distinct to avoid restart loops during dependency outages.

---

## 21. Backup Strategy

Backup follows DATABASE_DESIGN.md §29 and extends it to all project assets (DEVELOPMENT_WORKFLOW.md §24).

| Asset | Strategy | Frequency |
| ----- | -------- | --------- |
| **Database** | `pg_dump` logical backups + continuous WAL archiving (DATABASE_DESIGN.md §29) | Daily dump + WAL; retention 14 daily / 4 weekly / 3 monthly. |
| **Knowledge base** | Source documents versioned in the repo; index regenerable (Section 11.6) | With source control; index rebuilt on change. |
| **Uploaded files** | Persistent-volume backup (encrypted, off-box) | Daily (aligned with DB backup). |
| **Documentation** | In the repository (`docs/`), versioned with source | With source control. |
| **Configuration** | `.env.example` in repo; actual secrets in the secret store | Rotated/verified per policy (Section 13.2). |

**Rules:**
- Backups run on a dedicated schedule — never by hand (DATABASE_DESIGN.md §29).
- Backups are encrypted at rest; access restricted; no plaintext secrets (DATABASE_DESIGN.md §29).
- Monthly restore-and-verify drills validate backups (Section 22).

---

## 22. Restore Strategy

Restore follows the recovery objectives and runbook approach in DATABASE_DESIGN.md §29.

### 22.1 Database Restore

- Logical backups restored with `pg_restore`; WAL replayed for point-in-time recovery (DATABASE_DESIGN.md §29).
- Restore validated post-restore (integrity checks) before traffic resumes.
- Restore runbook lives in `docs/setup/` (DATABASE_DESIGN.md §29).

### 22.2 File Restore

- Uploaded-document volume restored from the latest valid backup; metadata reconciled with the database.

### 22.3 Knowledge Base Restore

- Source documents restored from version control (authoritative).
- The FAISS index is regenerated from source + chunk metadata — no fragile binary restore required (DATABASE_DESIGN.md §35).

### 22.4 Disaster Recovery

- Restore drills are scheduled and documented (Section 23).
- Recovery objectives (RPO/RTO) are met per DATABASE_DESIGN.md §29: RPO ≤ 15 minutes (WAL), RTO ≤ 60 minutes.

---

## 23. Disaster Recovery Plan

The disaster recovery plan defines how the platform recovers from major failures.

### 23.1 Failure Detection

- Health checks (Section 20) and monitoring (Section 19) detect: host/container failure, database outage, AI gateway outage, index loss, and degraded performance.
- Alert thresholds trigger the recovery workflow automatically or operator-initiated.

### 23.2 Recovery Steps

1. Assess scope: application, database, infrastructure, or external dependency.
2. Restore or rebuild the failed component per Section 22.
3. Validate health and readiness before resuming traffic (Section 20).
4. Verify monitoring returns to normal thresholds (Section 19).

### 23.3 Backup Recovery

- Database restored to the last valid point (WAL for PITR) (Section 22.1).
- Files restored from the latest valid backup (Section 22.2).
- Regenerable assets (index) rebuilt from source (Section 22.3).

### 23.4 Rollback Strategy

- Application rollback to the previous stable release (Section 30).
- Configuration rollback to the last known-good state.
- Schema rollback via the Alembic downgrade path where applicable (DATABASE_DESIGN.md §28).

### 23.5 Recovery Objectives

| Objective | Target | Source |
| --------- | ------ | ------ |
| **RPO** | ≤ 15 minutes (production) | DATABASE_DESIGN.md §29 (WAL) |
| **RTO** | ≤ 60 minutes | DATABASE_DESIGN.md §29 |
| **Index rebuild** | Regenerated from source | DATABASE_DESIGN.md §35 |

---

## 24. Security Strategy

Security in deployment follows BACKEND_ARCHITECTURE.md §22, DATABASE_DESIGN.md §30, and TESTING_STRATEGY.md §15.

| Control | Implementation |
| ------- | -------------- |
| **HTTPS** | TLS terminated at the proxy; all traffic encrypted (Section 15). |
| **Firewall** | Only the proxy is publicly reachable; internal services isolated (Section 7.5). |
| **Authentication** | JWT + server-side sessions per API_SPECIFICATION.md §3–5. |
| **Authorization** | Server-enforced RBAC and owner-scoping (BACKEND_ARCHITECTURE.md §10; DATABASE_DESIGN.md §30). |
| **Secure headers** | CSP, frame/cache protections at the proxy (Section 14.5). |
| **Data encryption** | At rest (backups, volumes) and in transit (TLS). |
| **Secret protection** | Secrets in the secret store only; never in code/images/logs (Section 13). |
| **Least privilege** | Dedicated roles; default-deny access (DATABASE_DESIGN.md §30.1). |

**Rules:**
- Security is validated before every release (TESTING_STRATEGY.md §31.4).
- Dependency security is audited in CI (DEVELOPMENT_WORKFLOW.md §26.4).
- Any suspected exposure triggers secret rotation immediately (Section 13.2).

---

## 25. Performance Optimization

Performance in production follows the budgets and strategies in API_SPECIFICATION.md §36, AI_ARCHITECTURE.md §32, and DATABASE_DESIGN.md §31.

| Technique | Application |
| --------- | ----------- |
| **Caching** | Caching headers for static/public data; short TTLs; future Redis for hot retrievals (API_SPECIFICATION.md §36.4; BACKEND_ARCHITECTURE.md §23). |
| **Compression** | gzip/br on JSON responses where beneficial (API_SPECIFICATION.md §36.3). |
| **Lazy loading** | Heavy AI initialization deferred until needed (BACKEND_ARCHITECTURE.md §23); frontend lazy loading (ui-ux-design.md §32). |
| **Database optimization** | Indexed hot paths, keyset pagination, bounded pools (DATABASE_DESIGN.md §31). |
| **API optimization** | Bounded payloads, field selection, background jobs for long ops (API_SPECIFICATION.md §36). |
| **AI optimization** | Concise prompts, metadata filtering, top-K tuning, in-memory index (AI_ARCHITECTURE.md §32). |

---

## 26. Scalability Strategy

Scaling follows the stateless-node design (BACKEND_ARCHITECTURE.md §23). Future scaling is planned; the architecture supports it without redesign.

### 26.1 Horizontal Scaling

- Add backend/worker instances behind the reverse proxy (with a future load balancer, Section 27).
- Stateless nodes make horizontal scale-in/out safe (state lives in the database).

### 26.2 Vertical Scaling

- Increase resources of the database server (CPU/RAM/disk) when load grows.
- Validated by load/stress testing (TESTING_STRATEGY.md §16.6).

### 26.3 Database Scaling

- Move to managed PostgreSQL/pgvector; read replicas for read-heavy loads (future).
- Index and query tuning before scaling (DATABASE_DESIGN.md §31).

### 26.4 AI Scaling

- Embedding/retrieval scale with memory and concurrency; LLM calls scale with quota/limits (AI_ARCHITECTURE.md §31.3).
- FAISS index shared via a regenerable copy; scale-out via replicated instances (Section 11.5).

### 26.5 Load Distribution

- A future load balancer distributes traffic across backend instances (Section 27).
- Worker load is distributed by the job/queue design (Section 9.4).

---

## 27. Load Balancing

Load balancing is a future enhancement; the architecture is designed for it now.

### 27.1 Future Load Balancer

- A dedicated load balancer (or LB-capable proxy tier) distributes external traffic across frontend/backend instances.
- The reverse proxy remains the TLS/entry point; the LB adds distribution and health-based routing (Section 20).

### 27.2 Traffic Distribution

- Round-robin/least-connections across stateless API nodes.
- Health-based routing: only ready instances receive traffic (Section 20.5).

### 27.3 High Availability

- Multiple instances remove the application layer as a single point of failure.
- Database high availability (managed HA, replicas) is a future step (Section 26.3).
- Session state in the DB makes instance loss transparent (DATABASE_DESIGN.md §25).

---

## 28. Deployment Workflow

Deployment follows the controlled sequence in DEVELOPMENT_WORKFLOW.md §30 and the validation gates in TESTING_STRATEGY.md §31.

### 28.1 Build

- Build the release artifact (images) from versioned source; images tagged with the release version (Section 6.4).
- Build passes with no errors/warnings (TESTING_STRATEGY.md §31.1).

### 28.2 Validation

- CI validates: full fast suite, contract, smoke (TESTING_STRATEGY.md §21.2).
- Staging validates the candidate in a production-like topology (Section 4).

### 28.3 Deployment

- Apply the migration step first (Section 7.3, 9.5).
- Deploy services in dependency order; the proxy last (Section 7.3).

### 28.4 Verification

- Post-deploy smoke verifies health, database, vector store, and AI gateway reachability (TESTING_STRATEGY.md §21.3; Section 20).

### 28.5 Monitoring

- Post-deploy monitoring tracks health, errors, latency, and AI metrics (Section 19).
- A degraded state triggers the rollback path (Section 30).

### 28.6 Rollback

- A failed verification or degraded monitoring triggers rollback to the previous stable release (Section 30).

---

## 29. Release Management

Release management follows DEVELOPMENT_WORKFLOW.md §22 and the versioning strategy in DEVELOPMENT_WORKFLOW.md §23.

### 29.1 Release Planning

- Releases are scoped (version, features, fixes, acceptance criteria, schedule).
- Release candidates are cut from `develop` via a `release/<version>` branch (DEVELOPMENT_WORKFLOW.md §9).

### 29.2 Release Validation

- Full regression, performance, and security suites on the release candidate (TESTING_STRATEGY.md §31).
- Staging validation: E2E critical journeys, smoke tests, UAT sign-off (TESTING_STRATEGY.md §21–22).
- AI evaluation metrics checked against the baseline (AI_ARCHITECTURE.md §38.3).

### 29.3 Production Release

- Merge `release/<version>` to `main`; tag the version (DEVELOPMENT_WORKFLOW.md §22.4).
- Deploy per the workflow (Section 28); post-deploy smoke validates (Section 20).

### 29.4 Emergency Release

- Urgent defects ship via `hotfix/*` branches merged to `main` and `develop` (DEVELOPMENT_WORKFLOW.md §9, §22).
- Emergency releases still pass smoke and targeted validation before deploy.

### 29.5 Rollback

- Any release that fails post-deploy verification rolls back per Section 30.

---

## 30. Rollback Strategy

Rollback is a first-class, rehearsed capability — not a last resort.

| Rollback type | Approach |
| ------------- | -------- |
| **Application rollback** | Redeploy the previous stable release (immutable image tags, Section 6.4). |
| **Database rollback** | Schema downgrade via Alembic where applicable; otherwise restore to the last valid backup + PITR (Section 22.1). |
| **Configuration rollback** | Revert to the last known-good configuration scope (Section 16 in DEVELOPMENT_WORKFLOW.md). |
| **AI rollback** | Revert model/config/prompt version to the last validated baseline (AI_ARCHITECTURE.md §38.3). |

**Rules:**
- Rollback is triggered automatically on failed verification and operator-confirmed on degraded monitoring (Section 28.5).
- Post-rollback analysis drives a corrective release (DEVELOPMENT_WORKFLOW.md §22.5).
- Rollback paths are rehearsed so they are fast and trusted.

---

## 31. Maintenance Strategy

Maintenance keeps the platform secure, current, and healthy (DEVELOPMENT_WORKFLOW.md §3.6).

| Area | Strategy |
| ---- | -------- |
| **Scheduled maintenance** | Planned windows for infra, dependency, and migration maintenance; communicated; low-traffic timing. |
| **Security updates** | Prioritized; validated in testing before production (DEVELOPMENT_WORKFLOW.md §26.4). |
| **Dependency updates** | Regular, reviewed, regression-tested (DEVELOPMENT_WORKFLOW.md §15.4). |
| **Database maintenance** | VACUUM/index maintenance, retention/purge jobs, and backup verification (DATABASE_DESIGN.md §35). |
| **AI maintenance** | Model/config reviews, prompt and KB updates through the evaluation loop (AI_ARCHITECTURE.md §38.3). |

**Rules:**
- Maintenance changes follow the same workflow and gates as feature work.
- No maintenance change bypasses testing or rollback readiness.

---

## 32. Operational Checklist

Deployment readiness is confirmed with this checklist before any production deployment.

| # | Check | Confirmed by |
| - | ----- | ------------ |
| 1 | **Configuration complete** | All environment variables and secrets set from the secret store (Sections 12–13). |
| 2 | **Environment ready** | Target environment provisioned and isolated; `ENVIRONMENT` correct (Section 4). |
| 3 | **Database ready** | Migrations applied; backups configured; least-privilege role verified (Section 10). |
| 4 | **APIs verified** | Health endpoints report ready; smoke tests pass (Sections 20, 28.4). |
| 5 | **AI ready** | Vector store present/reachable; model config validated; AI gateway reachable (Section 11). |
| 6 | **Security verified** | HTTPS, headers, secrets, and roles validated (Section 24). |
| 7 | **Testing passed** | Full validation gates green (TESTING_STRATEGY.md §31). |
| 8 | **Documentation updated** | Release notes and ops docs current (Section 18 in DEVELOPMENT_WORKFLOW.md). |

---

## 33. Production Readiness Checklist

A release is production-ready only when all of the following hold.

| Area | Requirement |
| ---- | ----------- |
| **Security** | HTTPS enforced; no secrets exposed; secure headers; roles least-privileged (Section 24). |
| **Performance** | Budgets met; no regressions against baseline (Section 25; TESTING_STRATEGY.md §31.3). |
| **Monitoring** | Health/error/AI/perf monitoring active with alerts (Section 19). |
| **Logging** | Structured logs flowing; no secrets logged (Section 18). |
| **Backup** | Backups scheduled, encrypted, and verified by restore drill (Section 21–22). |
| **Health checks** | Liveness/readiness working; orchestrator routing verified (Section 20). |
| **Testing** | All gates green; no open blockers (TESTING_STRATEGY.md §31). |
| **Documentation** | Deployment/ops documentation current (DEVELOPMENT_WORKFLOW.md §18). |

---

## 34. Future Deployment Improvements

Future enhancements extend the deployment strategy as the platform grows (PROJECT_RULES.md Future Scope; BACKEND_ARCHITECTURE.md §23). These are placeholders until the corresponding phases begin.

| Capability | Description |
| ---------- | ----------- |
| **CI/CD Pipeline** | Fully automated pipeline from merge to production deployment with gated promotion (DEVELOPMENT_WORKFLOW.md §28, §30). |
| **Kubernetes** | Container orchestration for large-scale scheduling, self-healing, and scaling. |
| **Cloud Deployment** | Managed services: PostgreSQL/pgvector, object storage, managed AI gateways, and secret managers. |
| **Auto Scaling** | Automatic horizontal scaling of API/workers based on load metrics (Section 26). |
| **CDN** | Content delivery for static assets and, where appropriate, cached API responses (Section 8.2). |
| **Object Storage** | Managed blob storage for uploads and backups, replacing local volumes (Section 17). |
| **Multi-Region Deployment** | Regional replicas and failover for high availability (Sections 26–27). |
| **Blue-Green Deployment** | Two-environment switchover for zero-downtime releases. |
| **Canary Deployment** | Gradual traffic shift to a new version with monitored rollback. |

**Roadmap rules:**
- Future items are planned through the documented workflow: research → design → phases → tests → release (DEVELOPMENT_WORKFLOW.md §36).
- Every future capability preserves the stateless-node, additively versioned design principles (Sections 1.3, 1.7).

---

## Important

This document is the **permanent deployment architecture guide** and the **single source of truth for all deployment and operational decisions** in the project.

It must be read together with:

- **PROJECT_RULES.md** — master project rules (tech stack, environment variables, performance & security).
- **docs/architecture/BACKEND_ARCHITECTURE.md** — stateless API, layers, and Deployment Readiness (§27).
- **docs/architecture/DATABASE_DESIGN.md** — schema, migrations, backup, retention, and security rules.
- **docs/architecture/AI_ARCHITECTURE.md** — AI monitoring, availability, and fallback behavior.
- **docs/architecture/API_SPECIFICATION.md** — health checks, API performance, and security rules.
- **docs/architecture/TESTING_STRATEGY.md** — deployment validation, smoke tests, and environments.
- **docs/architecture/DEVELOPMENT_WORKFLOW.md** — release management, rollback, and operational process.

All deployment work — infrastructure, Docker files, orchestration, proxy configuration, CI/CD, monitoring, and backup — must be derived from this document. Any implementation that deviates from this design must be corrected before it is accepted.

**This document is architecture and documentation only.** It contains no Dockerfiles, no compose files, no Nginx configuration, no shell scripts, no CI/CD YAML, no Python, and no SQL. Implementation is derived from these standards, following the project's Development Rules and Definition of Done.

---

## 1. Project Overview

The **Agentic AI-Based University Workflow Automation System** is a research-based Final Year Project for **Sindh Madressatul Islam University (SMIU)**. It is a **Multi-Agent AI Student Support Platform** built with **LangChain** and **LangGraph** that automates real university workflows — admissions, examinations, and general inquiries — rather than acting as a simple chatbot.

### The University Problem It Solves

Students frequently need accurate, timely information about admissions, examinations, and university procedures. This information lives in scattered documents and departments, creating:

- **Slow and inconsistent responses** to repeated student queries.
- **Delayed request handling** across admission and examination workflows.
- **An unmanaged knowledge base** that is hard for students to search.
- **Fragmented processes** with no tracked, automated resolution path.

### The Solution

A single platform where students ask questions in natural language and the system **routes, processes, and resolves** their needs end to end:

- A **Coordinator Agent** detects intent and routes requests to the correct specialist.
- **Specialist agents** (Admission, Examination, FAQ) answer grounded in the university knowledge base.
- **Retrieval-Augmented Generation (RAG)** grounds every answer in indexed university documents.
- **Automated workflows** carry requests through tracked statuses to resolution.

### Motivation

The project was motivated by the gap between a chatbot (which only answers questions) and real workflow automation. It demonstrates how modern **agentic AI** can automate university operations in a safe, grounded, and scalable way — producing a research-grade contribution to the field of university administrative automation.

### Why Agentic AI?

| Capability                       | Chatbot | Agentic AI (this project)    |
| -------------------------------- | ------- | ---------------------------- |
| Answers questions                | ✅      | ✅                           |
| Detects intent and routes        | ❌      | ✅ (Coordinator Agent)       |
| Resolves workflows end to end    | ❌      | ✅ (tracked requests)        |
| Grounded in university knowledge | Partial | ✅ (RAG over FAISS)          |
| Memory across turns              | Limited | ✅ (persisted conversations) |
| Safe, auditable behavior         | Limited | ✅ (guardrails + audit logs) |

Agentic AI was selected because it transforms the system from a **passive answerer** into an **active workflow executor** — the core research contribution of the project.

---

## 2. Features

### 🎓 Student Features

- Student registration and secure JWT-based login.
- Personal dashboard showing requests and recent activity.
- AI chat interface with conversation history and resume support.
- Request submission and status tracking.
- Profile and settings management.

### 🤖 AI Features

- **Coordinator Agent** — intent detection and routing (LangGraph).
- **Admission Agent** — admission requirements, eligibility, documents, merit queries, admission process.
- **Examination Agent** — date sheets, results, admit cards, examination rules, improvement policy.
- **FAQ Agent** — general university FAQs, departments, office timings, campus and contact information.
- Professional, concise, grounded responses with clear next steps.

### 📚 RAG Features

- Retrieval-Augmented Generation over an indexed university knowledge base.
- Sentence Transformers embeddings with a FAISS vector store.
- Grounded answers with **collapsible citations** ("Sources: 2" → expand).
- Metadata-filtered retrieval by category (admission / examination / faq / documents).

### 🗂️ Request Management

- Automated request lifecycle with tracked status (`request_timeline`).
- Status transitions from submission through resolution.
- Full audit trail of every request step.

### 🔐 Authentication

- JWT access + refresh tokens with server-side sessions.
- Password hashing (bcrypt/argon2 family) — never plaintext.
- Email verification and password reset flows.
- Rate-limited login to prevent brute force.

### 📊 Dashboard

- Student dashboard with request status, recent activity, and quick actions.
- Responsive, accessible design at all breakpoints.

### 🔔 Notifications

- In-app notifications for request status changes and system updates.
- Priority-based notification model aligned with the UX design system.

### 📖 Knowledge Base

- Categorized university documents: admission, examination, faq, documents.
- Document versioning and re-indexing as background jobs.
- Regenerable FAISS index from versioned source documents.

### 💬 Conversation History

- Every message persisted (`chat_history`) with conversation lifecycle.
- Resume archived conversations with reconstructed memory.
- Owner-scoped — students see only their own conversations.

### 👥 Role-Based Access

- Server-enforced RBAC (student / admin / future AI operator).
- Owner-scoped data access — no cross-account leakage.

### 🛠️ Future Admin Features

- Admin dashboard for students, departments, and request management (future phase).
- Documented in the API specification and UI/UX architecture; not part of Phase 1.

---

## 3. System Architecture

<div align="center">

```
Student
   │
   ▼
Next.js Frontend
   │
   ▼
FastAPI Backend  ───►  PostgreSQL
   │
   ▼
Coordinator Agent (LangGraph)
   │
   ├──► Admission Agent
   ├──► Examination Agent
   └──► FAQ Agent
   │
   ▼
LangChain RAG  ───►  FAISS Vector Store
   │
   ▼
LLM (Gemini 2.5 Flash)
   │
   ▼
Grounded Response + Citations
```

</div>

| Layer                    | Responsibility                                                                                                                |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| **Frontend**       | Next.js 15 app (React 19, TypeScript, Tailwind CSS, shadcn/ui) serving the landing page, auth, dashboard, and chat interface. |
| **Backend**        | FastAPI REST API (`/api/v1`) with layered architecture: routers → services → repositories → database.                    |
| **Database**       | PostgreSQL (SQLite for local development) persisting all 16 tables.                                                           |
| **AI Layer**       | LangGraph workflow (Coordinator + specialists) and LangChain RAG orchestration.                                               |
| **Knowledge Base** | Versioned university documents in`knowledge/`; embedded into a FAISS vector store.                                          |
| **Authentication** | JWT access + refresh tokens with server-side sessions and RBAC.                                                               |

---

## 4. Technology Stack

### Frontend

| Technology   | Purpose                                            |
| ------------ | -------------------------------------------------- |
| Next.js 15   | App Router, server-side rendering, React framework |
| React 19     | UI component model                                 |
| TypeScript   | Strictly typed frontend and shared logic           |
| Tailwind CSS | Styling and design tokens                          |
| shadcn/ui    | Radix-based component foundation                   |

### Backend

| Technology     | Purpose                        |
| -------------- | ------------------------------ |
| FastAPI        | REST API and server-side logic |
| Python 3.13+   | Backend language               |
| SQLAlchemy 2.0 | ORM and data access            |
| Alembic        | Database migrations            |
| Pydantic v2    | Request/response validation    |

### Database

| Technology | Purpose                    |
| ---------- | -------------------------- |
| PostgreSQL | Production database        |
| SQLite     | Local development database |

### AI

| Technology              | Purpose                                     |
| ----------------------- | ------------------------------------------- |
| LangGraph               | Agent state machine and workflow engine     |
| LangChain               | Chains, tools, retrieval, LLM orchestration |
| Google Gemini 2.5 Flash | Primary LLM                                 |
| FAISS                   | Vector store for retrieval                  |
| Sentence Transformers   | Embedding model for query + corpus          |

### Authentication

| Technology    | Purpose                        |
| ------------- | ------------------------------ |
| JWT           | Signed access + refresh tokens |
| bcrypt/argon2 | Password hashing               |
| RBAC          | Role-based authorization       |

### Development Tools

| Technology              | Purpose                            |
| ----------------------- | ---------------------------------- |
| Docker / Docker Compose | Containerization and orchestration |
| Git / GitHub            | Version control and collaboration  |
| GitHub Actions          | CI pipelines (placeholders)        |
| Ruff / linters          | Python linting                     |
| ESLint / Prettier       | TypeScript linting and formatting  |

### Testing

| Technology        | Purpose                       |
| ----------------- | ----------------------------- |
| Pytest            | Backend and AI test framework |
| Playwright        | End-to-end UI tests           |
| Postman / OpenAPI | API contract validation       |
| Load tools        | Performance and load testing  |

### Deployment

| Technology     | Purpose                            |
| -------------- | ---------------------------------- |
| Docker         | Containerized services             |
| Docker Compose | Local and production orchestration |
| Nginx          | Reverse proxy, TLS, static assets  |

---

## 5. Folder Structure

```text
smiu-ai-assistant/
├── .github/
│   └── workflows/              # CI/CD pipeline definitions
├── ai/                         # LangChain + LangGraph AI service
│   ├── agents/                 #   Agent definitions (Coordinator, Admission, Examination, FAQ)
│   ├── chains/                 #   LCEL chains
│   ├── core/                   #   Shared config & infrastructure
│   ├── graphs/                 #   LangGraph state machines (workflow engine)
│   ├── knowledge_base/         #   Knowledge base ingestion & stores
│   ├── memory/                 #   Short / long-term agent memory
│   ├── prompts/                #   Versioned prompt templates
│   ├── rag/                    #   Retrieval, indexing, embeddings
│   ├── tools/                  #   Agent tools (incl. future university APIs)
│   ├── tests/                  #   AI unit / integration tests
│   └── main.py                 #   AI service entrypoint
├── backend/                    # FastAPI REST API
│   ├── app/
│   │   ├── api/v1/endpoints/   #   HTTP routers (auth, students, chat, requests, ...)
│   │   ├── core/               #   Config, security, JWT
│   │   ├── db/                 #   Database session & base
│   │   ├── middleware/         #   Logging, CORS, error handling
│   │   ├── models/             #   SQLAlchemy ORM models (16 tables)
│   │   ├── schemas/            #   Pydantic request/response schemas
│   │   ├── services/           #   Business logic & orchestration
│   │   └── utils/              #   Shared helpers
│   ├── alembic/                #   Database migrations
│   ├── tests/                  #   Backend unit / integration tests
│   └── main.py                 #   Backend entrypoint
├── database/                   # DB assets: init, seeds, backups
│   ├── init/
│   ├── seeds/
│   └── backups/
├── docker/                     # Docker Compose stacks
│   ├── docker-compose.yml       #   Production stack
│   └── docker-compose.dev.yml   #   Development overrides
├── docs/                       # Architecture & documentation
│   └── architecture/            #   Source-of-truth design documents
├── frontend/                   # Next.js 15 web application
│   ├── app/                    #   App Router pages (auth, dashboard, chat)
│   ├── components/             #   ui/ (shadcn), layout/, chat/
│   ├── hooks/                  #   Custom React hooks
│   ├── lib/                    #   API client, utilities
│   ├── types/                  #   TypeScript types
│   ├── tests/                  #   Frontend component tests
│   ├── public/                 #   Static assets
│   └── styles/                 #   Global styles & tokens
├── knowledge/                  # University source documents & FAQs for RAG
│   ├── admission/
│   ├── examination/
│   ├── faq/
│   ├── documents/
│   └── vectorstore/            #   FAISS index files (generated, gitignored)
├── testing/                    # Cross-service suites
│   ├── e2e/
│   ├── integration/
│   └── load/
├── .env.example                # Shared environment template
├── .gitattributes
├── .gitignore
├── LICENSE                     # Project license
├── PROJECT_RULES.md            # Master development rules
└── README.md
```

> The folder layout is defined by **PROJECT_RULES.md** — all new code must land in its owning folder; no parallel or duplicate structures.

---

## 6. Prerequisites

| Tool           | Version | Notes                                           |
| -------------- | ------- | ----------------------------------------------- |
| Node.js        | 20+     | Required for the Next.js frontend               |
| Python         | 3.13+   | Required for backend and AI services            |
| PostgreSQL     | 16+     | Production database (SQLite used for local dev) |
| Git            | Latest  | Version control                                 |
| Docker         | Latest  | Optional — for containerized environments      |
| Docker Compose | Latest  | Optional — for orchestrated stacks             |

Additionally:

- **Python virtual environment** (`venv`) for the backend and AI services.
- **Package managers**: `npm` for the frontend, `pip` for Python.

---

## 7. Installation Guide

### 7.1 Clone Repository

```bash
git clone https://github.com/<your-org>/smiu-ai-assistant.git
cd smiu-ai-assistant
```

### 7.2 Frontend Installation

```bash
cd frontend
npm install
cp .env.example .env    # adjust variables as needed
```

### 7.3 Backend Installation

```bash
cd ../backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

The AI service (`ai/`) follows the same pattern with its own virtual environment.

### 7.4 Environment Variables

Copy the shared template and adjust values (never commit real secrets):

```bash
cp .env.example .env
```

See **Section 8** for the full variable reference.

### 7.5 Database Setup

For local development, SQLite is used by default (no setup required). For PostgreSQL:

```bash
# Option A: use the provided Docker database
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up db
```

### 7.6 Alembic Migration

```bash
cd backend
alembic upgrade head
```

### 7.7 Start Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 7.8 Start Frontend

```bash
cd frontend
npm run dev
```

The frontend is available at `http://localhost:3000` and the API docs at `http://localhost:8000/docs`.

---

## 8. Environment Variables

> Actual secret values are **never** committed or documented. The table below documents the required variables and their purpose. All variables are defined in `.env.example` and per-service templates (`frontend/.env.example`, `backend/.env.example`, `ai/.env.example`).

### Frontend

| Variable                | Purpose                                      |
| ----------------------- | -------------------------------------------- |
| `NEXT_PUBLIC_API_URL` | Backend API base URL for the frontend client |
| `FRONTEND_PORT`       | Local frontend server port                   |

### Backend

| Variable         | Purpose                                                                   |
| ---------------- | ------------------------------------------------------------------------- |
| `BACKEND_PORT` | Backend server port                                                       |
| `DATABASE_URL` | Database connection string (SQLite in dev, PostgreSQL in prod)            |
| `ENVIRONMENT`  | Active environment scope (`development` / `testing` / `production`) |
| `SECRET_KEY`   | App-level secret for encryption and signing                               |

### Database

| Variable              | Purpose                      |
| --------------------- | ---------------------------- |
| `POSTGRES_DB`       | PostgreSQL database name     |
| `POSTGRES_USER`     | PostgreSQL user              |
| `POSTGRES_PASSWORD` | PostgreSQL password (secret) |
| `POSTGRES_PORT`     | PostgreSQL port              |

### JWT

| Variable                        | Purpose                                     |
| ------------------------------- | ------------------------------------------- |
| `JWT_SECRET`                  | Secret for signing and verifying JWT tokens |
| `JWT_ALGORITHM`               | JWT signing algorithm (e.g.,`HS256`)      |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime                       |

### Gemini API

| Variable                 | Purpose                                      |
| ------------------------ | -------------------------------------------- |
| `GEMINI_API_KEY`       | LLM API key for Gemini 2.5 Flash (secret)    |
| `LANGCHAIN_API_KEY`    | LangSmith / LangChain tracing key (optional) |
| `LANGCHAIN_TRACING_V2` | Enables LangChain tracing                    |
| `LANGCHAIN_PROJECT`    | LangSmith project name                       |

### FAISS

| Variable       | Purpose                                          |
| -------------- | ------------------------------------------------ |
| `FAISS_PATH` | File path to the FAISS vector index              |
| `RAG_TOP_K`  | Number of chunks retrieved per query (default 4) |

### Application Settings

| Variable                   | Purpose                                          |
| -------------------------- | ------------------------------------------------ |
| `AI_PORT`                | AI service port                                  |
| `CHAT_HISTORY_LIMIT`     | Conversation memory window in turns (default 20) |
| `NEXT_PUBLIC_AI_API_URL` | AI service base URL for the frontend             |

---

## 9. Running the Project

### Development Mode

```bash
# Terminal 1 — backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — AI service
cd ai && uvicorn main:app --reload --port 8001

# Terminal 3 — frontend
cd frontend && npm run dev
```

Uses SQLite for fast iteration; the LLM is mocked/gated by default with the option to enable the real model.

### Production Mode

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

Builds and starts the full stack: reverse proxy, frontend, backend, worker, and database with production configuration.

### Testing Mode

Run the automated suites per the testing strategy:

```bash
cd backend && pytest
cd ai && pytest
cd frontend && npm run test
cd testing && npm run test:e2e
```

---

## 10. Project Workflow

A student request flows through the system as follows:

<div align="center">

```
Student
   │  sends a natural-language message
   ▼
API (FastAPI)
   │  authenticates, validates, routes
   ▼
Coordinator Agent (LangGraph)
   │  detects intent
   ▼
Specialized Agent (Admission / Examination / FAQ)
   │  scopes retrieval
   ▼
RAG (LangChain → FAISS)
   │  retrieves relevant chunks
   ▼
Gemini 2.5 Flash
   │  generates a grounded answer
   ▼
Response
   │  answer + citations
   ▼
Database
   │  persists conversation, sources, logs
   ▼
UI (Next.js)
   │  renders streamed answer with sources
   ▼
Student
```

</div>

Each step is logged with a correlation ID and auditable — every answer is grounded and traceable (AI_ARCHITECTURE.md §11).

---

## 11. AI Workflow

| Stage                  | Description                                                                                                                                                      |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Coordinator**  | Entry node of the LangGraph state machine; detects the user's intent and routes to the correct specialist (AI_ARCHITECTURE.md §9).                              |
| **Routing**      | The router selects Admission, Examination, or FAQ based on the intent signal; low-confidence intents trigger a clarifying question (AI_ARCHITECTURE.md §9.5).   |
| **RAG**          | Retrieval-Augmented Generation grounds every answer in the indexed knowledge base — retrieval always precedes generation (PROJECT_RULES.md AI Behaviour Rules). |
| **Retrieval**    | The query is embedded with the same Sentence Transformer; FAISS returns the top-K relevant chunks scoped by category (AI_ARCHITECTURE.md §16).                  |
| **Generation**   | Gemini 2.5 Flash produces a grounded, formatted answer within the context budget (AI_ARCHITECTURE.md §18).                                                      |
| **Memory**       | Short-term memory keeps the recent window (default 20 turns); optional long-term summaries reconstruct context on resume (AI_ARCHITECTURE.md §21).              |
| **Conversation** | Messages persist in`chat_history`; conversations have a full lifecycle (create → active → archived → restore/delete).                                       |
| **Feedback**     | Students rate responses; feedback feeds the evaluation loop and drives prompt/knowledge improvements (AI_ARCHITECTURE.md §29, §38).                            |

---

## 12. Database Overview

The schema (16 tables) is defined in **DATABASE_DESIGN.md** and managed with **SQLAlchemy 2.0 + Alembic**.

| Table                   | Purpose                                                     |
| ----------------------- | ----------------------------------------------------------- |
| `users`               | Application accounts (students, admins)                     |
| `students`            | Student profile and university information (1:1 with users) |
| `departments`         | University departments and agent mapping                    |
| `ai_conversations`    | AI chat sessions and lifecycle state                        |
| `chat_history`        | Messages within conversations                               |
| `requests`            | Core workflow requests (admission/examination/etc.)         |
| `request_timeline`    | Append-only status history for each request                 |
| `notifications`       | User-facing activity feed and toasts                        |
| `documents`           | Uploaded files with checksums                               |
| `knowledge_documents` | Knowledge base document metadata and versions               |
| `knowledge_chunks`    | Chunked text with source metadata for retrieval             |
| `ai_sources`          | Citations attached to AI messages                           |
| `feedback`            | User ratings, comments, and flags                           |
| `audit_logs`          | Append-only security and audit events                       |
| `agent_logs`          | AI routing, retrieval, and execution logs                   |
| `sessions`            | Auth sessions and token records                             |

---

## 13. API Overview

The REST API is organized under `/api/v1` and fully specified in **API_SPECIFICATION.md**. It follows REST conventions with uniform JSON envelopes and consistent error shapes.

| Area                     | Endpoints                                                            | Auth                |
| ------------------------ | -------------------------------------------------------------------- | ------------------- |
| **Authentication** | Register, login, refresh, logout, password reset, email verification | Public / token      |
| **Students**       | Profile, settings, owner-scoped account management                   | JWT (student)       |
| **Requests**       | Create, list, retrieve, track workflow requests                      | JWT (owner)         |
| **Chat**           | Send message, list conversations, resume, delete                     | JWT (owner)         |
| **AI**             | Chat completions, feedback, citation sources                         | JWT                 |
| **Notifications**  | List, read, mark-as-read                                             | JWT (owner)         |
| **Knowledge Base** | Read-side access to indexed documents                                | JWT / public        |
| **Admin (future)** | Student/department/request administration                            | Admin role (future) |

Every endpoint documents its request/response schema, status codes, and error envelope (API_SPECIFICATION.md §30).

---

## 14. Security Features

| Feature                               | Implementation                                                                  |
| ------------------------------------- | ------------------------------------------------------------------------------- |
| **JWT**                         | Short-lived signed access tokens + server-side refresh sessions                 |
| **Role-Based Access**           | Server-enforced RBAC; owner-scoped data access                                  |
| **Password Hashing**            | Strong salted hashing (bcrypt/argon2 family) — never plaintext                 |
| **Input Validation**            | Pydantic v2 at every boundary (client + server)                                 |
| **Prompt Injection Protection** | Input treated as data; guardrails on input and output (AI_ARCHITECTURE.md §26) |
| **Rate Limiting**               | Login and API rate limits (API_SPECIFICATION.md §13)                           |
| **Secure File Upload**          | Type/size/checksum validation; UUID-based safe filenames                        |
| **PII Protection**              | Redacted logs; owner-scoped data; consent-respecting retention                  |
| **HTTPS**                       | TLS enforced at the reverse proxy in production (DEPLOYMENT.md §15)            |

---

## 15. Testing

The complete strategy is defined in **TESTING_STRATEGY.md** — the single source of truth for all testing decisions.

| Level                         | Scope                                                                       |
| ----------------------------- | --------------------------------------------------------------------------- |
| **Unit Testing**        | Isolated services, repositories, components, and prompt modules             |
| **Integration Testing** | Services + repositories + database; routes + services                       |
| **API Testing**         | Contracts, status codes, error envelopes, pagination/filter/sort            |
| **AI Testing**          | Routing, grounding, citations, hallucination prevention, evaluation metrics |
| **UI Testing**          | Components, forms, accessibility, responsive, UI states                     |
| **Performance Testing** | Latency budgets, load, stress, scalability                                  |
| **Security Testing**    | Auth, RBAC, injection, XSS, CSRF, prompt injection, PII                     |

Quality gates (TESTING_STRATEGY.md §31) block releases until all suites pass.

---

## 16. Deployment

The complete deployment and operational strategy is defined in **DEPLOYMENT.md** — the single source of truth for deployment decisions.

| Area                            | Strategy                                                               |
| ------------------------------- | ---------------------------------------------------------------------- |
| **Frontend Deployment**   | Containerized Next.js production build behind the reverse proxy        |
| **Backend Deployment**    | Stateless FastAPI container(s) + background worker                     |
| **Database Deployment**   | PostgreSQL with persistent storage, least-privilege roles              |
| **Environment Variables** | Injected per environment from the secret store; never committed        |
| **Production Checklist**  | Operational + production readiness checklists (DEPLOYMENT.md §32–33) |

Deployment follows the controlled workflow: build → validate → deploy → health check → monitor → rollback (DEPLOYMENT.md §28).

---

## 17. Performance

Performance budgets are defined in **API_SPECIFICATION.md §36** and **AI_ARCHITECTURE.md §31**.

| Area                             | Target / Strategy                                                                              |
| -------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Expected response time** | Read/write/health endpoints sub-second at p95; AI bounded by model latency with optimized TTFT |
| **Caching**                | Caching headers for public/static data; short TTLs                                             |
| **Connection pooling**     | Sized async DB pools; no per-request connect overhead                                          |
| **Optimized queries**      | Indexed hot paths; keyset pagination; efficient counts                                         |
| **RAG optimization**       | Metadata filtering, top-K tuning, in-memory FAISS index                                        |
| **Streaming responses**    | Token-by-token streaming with TTFT optimization (future SSE)                                   |

---

## 18. Future Improvements

| Capability                                                                             | Status        |
| -------------------------------------------------------------------------------------- | ------------- |
| Admin Panel                                                                            | Future phase  |
| Additional AI Agents (Finance, Registration, Scholarship, Library, Hostel, IT Support) | Future phases |
| Voice Assistant                                                                        | Future        |
| OCR for document intake                                                                | Future        |
| Email Integration                                                                      | Future        |
| Analytics & usage dashboards                                                           | Future        |
| Multi-language Support                                                                 | Future        |
| Mobile Application                                                                     | Future        |
| Live Notifications (WebSockets)                                                        | Future        |

See **DEVELOPMENT_WORKFLOW.md §36** and **PROJECT_RULES.md Future Scope** for the full roadmap.

---

## 19. Documentation

All documentation lives in the repository and is the permanent reference for development.

| Document                                      | Description                                                                          |
| --------------------------------------------- | ------------------------------------------------------------------------------------ |
| `PROJECT_RULES.md`                          | Master development guide — project rules, tech stack, standards, Definition of Done |
| `docs/architecture/ui-ux-design.md`         | UI/UX architecture — the only design source for the frontend                        |
| `docs/architecture/BACKEND_ARCHITECTURE.md` | Backend architecture — layers, services, auth, security, testing                    |
| `docs/architecture/DATABASE_DESIGN.md`      | Database design — 16 tables, transactions, retention, backups                       |
| `docs/architecture/AI_ARCHITECTURE.md`      | AI architecture — agents, LangGraph, RAG, guardrails, evaluation                    |
| `docs/architecture/API_SPECIFICATION.md`    | API specification — every endpoint, contract, and error code                        |
| `docs/architecture/TESTING_STRATEGY.md`     | Testing strategy — levels, coverage, quality gates                                  |
| `docs/architecture/DEVELOPMENT_WORKFLOW.md` | Development workflow — lifecycle, Git, coding standards, releases                   |
| `docs/architecture/DEPLOYMENT.md`           | Deployment — infrastructure, security, monitoring, backup, recovery                 |
| `docs/architecture/IMPLEMENTATION_PLAN.md`  | Official implementation roadmap for the project                                      |
| `README.md`                                 | This document — repository overview and quick start                                 |

---

## 20. Contributing Guidelines

### Branch Naming

| Branch        | Convention                                |
| ------------- | ----------------------------------------- |
| `main`      | Production-ready, always deployable       |
| `develop`   | Integration branch for completed features |
| `feature/*` | One branch per feature                    |
| `bugfix/*`  | Non-urgent defect fixes                   |
| `hotfix/*`  | Urgent production fixes                   |
| `release/*` | Release preparation                       |

### Commit Messages

Use conventional commits: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `perf`, `build`, `ci`, `chore` — one logical change per commit.

### Coding Standards

- Strict TypeScript (no `any`) and strict Python typing.
- Follow the layer and folder rules in PROJECT_RULES.md.
- Reuse existing components, services, and utilities before writing new ones.

### Pull Requests

- One feature/fix per PR, targeting `develop`.
- All automated suites must pass.
- Describe what, why, and how; link the task.

### Code Reviews

- At least one reviewer besides the author for non-trivial changes.
- Review for readability, maintainability, architecture compliance, security, performance, testing, and documentation.

---

## 21. License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

> License text to be finalized by the project team and the university.

---

## 22. Authors

**Final Year Project Team**

- Final Year Project Students
- Department of Computer Science
- Sindh Madressatul Islam University (SMIU)
- Academic Supervisor: *(to be added)*

---

## 23. Acknowledgements

This project builds upon the work of the following open-source and research communities:

| Project               | Acknowledged for                         |
| --------------------- | ---------------------------------------- |
| Google Gemini         | Primary LLM powering grounded responses  |
| LangChain             | Retrieval chains and LLM orchestration   |
| LangGraph             | Agent state machines and workflow engine |
| FastAPI               | Async, typed REST API framework          |
| Next.js               | React application framework              |
| shadcn/ui             | Accessible component foundation          |
| PostgreSQL            | Production database                      |
| SQLAlchemy            | ORM and data access                      |
| Alembic               | Database migrations                      |
| FAISS                 | Vector search over the knowledge base    |
| Sentence Transformers | Embedding model for retrieval            |

---

## 24. Repository Badges

| Badge          | Status                                                           |
| -------------- | ---------------------------------------------------------------- |
| Build          | ![Build](https://img.shields.io/badge/build-passing-brightgreen) |
| License        | ![License](https://img.shields.io/badge/license-MIT-blue)        |
| Python Version | ![Python](https://img.shields.io/badge/python-3.13%2B-3776AB)    |
| Node Version   | ![Node](https://img.shields.io/badge/node-20%2B-339933)          |
| FastAPI        | ![FastAPI](https://img.shields.io/badge/FastAPI-009688)          |
| Next.js        | ![Next.js](https://img.shields.io/badge/Next.js-15-000000)       |
| PostgreSQL     | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1) |
| AI Powered     | ![AI Powered](https://img.shields.io/badge/AI-Powered-FF6F00)    |

---

Built for **Sindh Madressatul Islam University (SMIU)** — Department of Computer Science.

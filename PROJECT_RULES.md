



# PROJECT RULES



**Permanent Development Guide**



| Field                | Value                                                                                         |
| -------------------- | --------------------------------------------------------------------------------------------- |
| **Project**    | Agentic AI-Based University Workflow Automation System (Multi-Agent Student Support Platform) |
| **University** | Sindh Madressatul Islam University (SMIU)                                                     |
| **Version**    | 1.0.0                                                                                         |
| **Status**     | Active Development                                                                            |
| **Purpose**    | Permanent Development Guide                                                                   |

---

## Project Goal

This project is a **research-based Final Year Project** developed for **SMIU** (Sindh Madressatul Islam University). It focuses on building a **Multi-Agent AI Student Support Platform** using **LangChain** and **LangGraph**.

The system is designed to **automate university workflows** — such as admissions, examinations, and general inquiries — instead of acting as a simple chatbot. A chatbot only answers questions; this platform **routes, processes, and resolves** real university workflows end to end.

The platform:

- Uses **multiple specialized AI agents coordinated through LangGraph**, with a Coordinator Agent routing intents to the correct specialist.
- Retrieves answers using **Retrieval-Augmented Generation (RAG)**, grounded in a maintained university knowledge base.
- Powers knowledge retrieval with **LangChain** and a **FAISS** vector store.
- Routes and resolves student requests through automated workflows with tracked status.
- Provides a modern, professional, production-ready web experience for students, administrators, and AI operators.

Every decision in this codebase must serve this goal: a research-grade, scalable, multi-agent system that demonstrates real university workflow automation for SMIU.

---

## Project Scope

### Phase 1 (Current FYP)

| Area              | Deliverable                                            |
| ----------------- | ------------------------------------------------------ |
| Landing Page      | Public marketing page with hero, features, and CTA     |
| About             | University and project overview page                   |
| Contact           | Contact and support page                               |
| Authentication    | JWT-based student login and registration               |
| Student Dashboard | Personal dashboard for requests and activity           |
| AI Chat Interface | ChatGPT-style chat with the assistant                  |
| Coordinator Agent | Intent detection and routing (LangGraph)               |
| Admission Agent   | Admission-related queries and workflows                |
| Examination Agent | Exam date sheets, results, and rules                   |
| FAQ Agent         | General university FAQ answers                         |
| LangChain         | LLM orchestration and retrieval chains                 |
| LangGraph         | Agent state machine and workflow engine                |
| RAG               | Retrieval-Augmented Generation over the knowledge base |
| FAISS             | Vector store for retrieval                             |
| SQLite            | Development database                                   |

### Future Scope

Placeholders only — not part of Phase 1:

- Finance Agent
- Registration Agent
- Library Agent
- Hostel Agent
- Scholarship Agent
- ERP Integration
- LMS Integration
- Voice Assistant
- Mobile App

---

## Project Principles

- **Simplicity over complexity** — choose the simplest solution that works.
- **Reusability before duplication** — reuse before writing anything new.
- **Modular architecture** — small, independent, well-bounded modules.
- **Scalability** — design for growth from day one.
- **Maintainability** — code that is easy to read, change, and extend.
- **Production-quality code only** — no shortcuts, no throwaway code.
- **Small focused modules** — one responsibility per module.
- **Consistency across the project** — same patterns, naming, and structure everywhere.
- **Prefer updating existing code over creating new files.**

---

## Development Rules

Always follow these rules when writing any code:

- Write **clean, modular, and production-ready** code.
- **Avoid duplicate code.** Reuse existing utilities, components, and services before writing new ones.
- Follow a **scalable folder architecture** consistent with the existing project structure.
- Use **reusable components** (shadcn/ui primitives and feature-level composites).
- Use **TypeScript best practices**: strict typing, explicit interfaces, no `any`, no unused code.
- **Never generate unnecessary files.** Every file must have a clear purpose.
- Keep the codebase **maintainable**: small, focused modules with clear boundaries and meaningful names.
- Do not add comments unless they explain *why*, not *what*.

---

## Tech Stack

### Frontend

| Technology   | Usage                              |
| ------------ | ---------------------------------- |
| Next.js      | App Router, React framework        |
| TypeScript   | Typed frontend and shared logic    |
| Tailwind CSS | Styling and design tokens          |
| shadcn/ui    | Component foundation (Radix-based) |

### Backend

| Technology | Usage                          |
| ---------- | ------------------------------ |
| FastAPI    | REST API and server-side logic |
| Python     | Backend language               |

### AI

| Technology | Usage                                       |
| ---------- | ------------------------------------------- |
| LangChain  | Chains, tools, retrieval, LLM orchestration |
| LangGraph  | Agent state machines and workflow engine    |

### LLM

| Model                   | Status         |
| ----------------------- | -------------- |
| Google Gemini 2.5 Flash | Primary        |
| GPT-4o                  | Future support |

### Embeddings

| Provider          | Status   |
| ----------------- | -------- |
| Google Embeddings | Default  |
| OpenAI Embeddings | Optional |

### Database

| Environment | Database   |
| ----------- | ---------- |
| Development | SQLite     |
| Production  | PostgreSQL |

### RAG & Vector Store

| Component    | Technology                                                            |
| ------------ | --------------------------------------------------------------------- |
| Retrieval    | LangChain Retrieval (Retrieval-Augmented Generation)                  |
| Vector store | FAISS (initial), Postgres/`pgvector` or managed store in production |

### Deployment

| Technology     | Usage                              |
| -------------- | ---------------------------------- |
| Docker         | Containerization of all services   |
| Docker Compose | Local and production orchestration |

---

## Coding Standards

- Follow **clean architecture**: separate concerns into layers (presentation, application, domain, infrastructure).
- Write **modular code** — small, focused modules with single responsibilities.
- Use **reusable components** and shared utilities before writing anything new.
- Write **strict TypeScript**: explicit interfaces/types, no `any`, no unused or implicitly typed code.
- Write **proper Python typing**: type hints on all functions and models; use Pydantic for schemas.
- Enforce **layer separation** — never mix UI, business logic, and API calls in one place.
- Use **proper naming conventions**:
  - Components: `PascalCase`.
  - Hooks: `use`-prefixed, `camelCase`.
  - Functions and variables: `camelCase`.
  - Python modules/functions: `snake_case`.
  - Constants: `SCREAMING_SNAKE_CASE` / `UPPER_CASE`.
- **Separate UI, logic, and API.** Do not mix business logic into components or routes.
- **Always create responsive UI** — mobile-first, tested at all breakpoints.
- **Always use server actions or API routes where appropriate.** Keep sensitive logic (auth, database, LLM calls) on the server.
- Validation on both client (forms) and server (schemas).
- Handle errors explicitly; every error path must have a visible, friendly state.
- Write **production-ready code**: testable, typed, documented only where needed, and deployable.
- Follow the design tokens and component library defined in `docs/architecture/ui-ux-design.md`.

---

## Definition of Done

A feature is complete only when all of the following are satisfied:

- Responsive UI across breakpoints.
- No TypeScript errors.
- Proper Python typing on backend and AI code.
- Loading states implemented.
- Empty states implemented.
- Error states implemented.
- Validation completed on client and server.
- API documented.
- Documentation updated in `docs/`.
- PROJECT_RULES.md followed.
- Production-ready quality achieved.

---

## Naming Conventions

**Frontend:**

| Item       | Convention       |
| ---------- | ---------------- |
| Components | `PascalCase`   |
| Pages      | `kebab-case`   |
| Hooks      | `useSomething` |
| Functions  | `camelCase`    |
| Variables  | `camelCase`    |
| Constants  | `UPPER_CASE`   |
| Types      | `PascalCase`   |
| Interfaces | `PascalCase`   |

**Backend:**

| Item            | Convention     |
| --------------- | -------------- |
| Python Files    | `snake_case` |
| Functions       | `snake_case` |
| Variables       | `snake_case` |
| Classes         | `PascalCase` |
| Database Tables | `snake_case` |
| API Endpoints   | `kebab-case` |

---

## API Standards

- **REST API** — resource-based endpoints; use HTTP methods semantically.
- **JSON responses** — consistent, structured JSON for every response.
- **API versioning** — version under `/api/v1` to allow safe evolution.
- **Consistent error handling** — uniform error shape (error code, message, details).
- **HTTP status codes** — use the correct codes (200, 201, 400, 401, 403, 404, 422, 500).
- **Pydantic validation** — validate all requests and responses with Pydantic schemas.
- **Response schema consistency** — every endpoint documents its request/response schema.

---

## Git & Version Control Standards

**Branch strategy:**

| Branch        | Purpose                                          |
| ------------- | ------------------------------------------------ |
| `main`      | Production-ready, always deployable              |
| `develop`   | Integration branch for completed features        |
| `feature/*` | One branch per feature, branched from`develop` |

**Rules:**

- Never push broken code to `main` or `develop`.
- Small, focused commits.
- Meaningful commit messages describing *what* and *why*.
- One feature per branch.
- Pull Request required before any merge.

---

## Environment Variables

- Secrets must **never** be hardcoded in source code or committed to the repository.
- All secrets are loaded from a local `.env` file (gitignored); `.env.example` holds the template.

| Variable           | Purpose                                                        |
| ------------------ | -------------------------------------------------------------- |
| `GEMINI_API_KEY` | LLM API key for Gemini 2.5 Flash                               |
| `DATABASE_URL`   | Database connection string (SQLite in dev, PostgreSQL in prod) |
| `JWT_SECRET`     | Secret for signing and verifying JWT tokens                    |
| `FAISS_PATH`     | File path to the FAISS vector index                            |
| `SECRET_KEY`     | App-level secret for encryption and signing                    |

Add any new environment variable to `.env.example` when it is introduced.

---

## Database Overview

Initial tables:

| Table                   | Purpose                                          |
| ----------------------- | ------------------------------------------------ |
| `students`            | Student accounts and profile information         |
| `chat_history`        | Messages from AI conversations                   |
| `knowledge_documents` | Metadata for indexed knowledge base documents    |
| `agent_logs`          | Logs of agent executions, routing, and decisions |
| `sessions`            | Auth sessions and user tokens                    |

SQLite during development; PostgreSQL in production (see Tech Stack).

---

## Knowledge Base Structure

```
knowledge/
├── admission/       # Admission guides, eligibility, required documents
├── examination/     # Date sheets, results, exam rules
├── faq/             # General university FAQs
├── documents/       # Policies and official documents
└── vectorstore/     # FAISS index files (generated)
```

All university documents, FAQs, policies, and admission guides are indexed with **LangChain** and stored in **FAISS** for **Retrieval-Augmented Generation (RAG)**. Source files live in the category folders; the FAISS index is written to `vectorstore/`.

---

## Project Workflow

Development proceeds strictly in this order — each phase builds on the previous one. Do not skip ahead.

1. **Research** — study existing university support systems, LLM agent patterns, and RAG best practices.
2. **Planning** — define requirements, agent responsibilities, data sources, and milestones.
3. **UI/UX Design** — design the interface and user flows following `docs/architecture/ui-ux-design.md`.
4. **Frontend Development** — build the Next.js UI and reusable components.
5. **Backend Development** — implement the FastAPI REST API and business logic.
6. **Database Design** — design the schema, migrations, and seed data.
7. **AI Integration** — connect the LangChain/LangGraph agents to the backend.
8. **RAG Integration** — index the knowledge base and wire retrieval into the agents.
9. **Testing** — unit, integration, and end-to-end tests.
10. **Deployment** — Docker images, compose stacks, and CI/CD.

---

## Testing Standards

**Frontend:**

- Component Testing — render and behavior of individual components.
- UI Testing — user flows through the interface.
- Responsive Testing — layouts at all breakpoints.

**Backend:**

- API Testing — endpoint contracts, status codes, and responses.
- Unit Testing — isolated business logic.
- Integration Testing — services, database, and external calls together.

**AI:**

- Prompt Testing — prompt quality and consistency.
- Agent Routing Testing — Coordinator routes intents to the correct agent.
- Retrieval Testing — knowledge base retrieval relevance.
- RAG Validation — grounded, accurate answers.

**General:**

- Every important feature must be testable before deployment.

---

## UI Standard

The interface must represent a **modern university portal**:

- **Blue and White theme** — primary `#2563EB`, background `#F8FAFC`, white cards.
- **Professional landing page** for the public website.
- **Professional dashboards** for students and admins.
- **Rounded cards** — large border radius throughout.
- **Soft shadows** — subtle elevation, never harsh.
- **Clean typography** — Inter, consistent type scale, comfortable line height.
- **Consistent spacing** — token-based (4px scale), aligned rhythm across all pages.
- **Minimal design** — clean spacing, no visual clutter.
- **Modern design** — follow the design system in `docs/architecture/ui-ux-design.md`.
- **Responsive** — mobile, tablet, and desktop.
- **Accessible** — WCAG AA contrast, keyboard navigation, focus states, reduced-motion support.

---

## UI Pages Overview

| Page                     | Purpose                                                                                               |
| ------------------------ | ----------------------------------------------------------------------------------------------------- |
| Landing Page             | Public hero page introducing the platform                                                             |
| About                    | Project and university context                                                                        |
| Departments              | University departments and their AI agents                                                            |
| Contact                  | Contact and support                                                                                   |
| Login                    | Student authentication                                                                                |
| Student Portal           | All authenticated student features belong here — Dashboard, AI Chat, Chat History, Profile, Settings |
| Admin Dashboard (Future) | Administrative management (future phase)                                                              |

---

## AI Agents

**Phase 1 — implement only the following agents:**

| Agent                       | Responsibilities                                                                                             |
| --------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Coordinator Agent** | Detect user intent · route requests to the correct specialist · manage the workflow · aggregate responses |
| **Admission Agent**   | Admission requirements · eligibility · required documents · merit queries · admission process            |
| **Examination Agent** | Date sheet · results · admit cards · examination rules · improvement policy                              |
| **FAQ Agent**         | General university FAQs · departments · office timings · campus information · contact information        |

**Future agents — leave placeholders only:**

- Finance Agent
- Registration Agent
- Library Agent
- IT Support Agent
- Hostel Agent
- Scholarship Agent

Agent modules live under `ai/agents/` and must follow the existing folder structure and naming conventions.

---

## AI Development Roadmap

| Phase             | Agents / Features                                                             |
| ----------------- | ----------------------------------------------------------------------------- |
| **Phase 1** | Coordinator Agent · Admission Agent · Examination Agent · FAQ Agent        |
| **Phase 2** | Registration Agent · Finance Agent · Scholarship Agent                      |
| **Phase 3** | Library Agent · Hostel Agent · IT Support Agent                             |
| **Phase 4** | ERP Integration · LMS Integration · Voice Assistant · Multilingual Support |

Only **Phase 1** will be implemented in the current Final Year Project.

---

## LangGraph Workflow

```
Student
   ↓
Next.js UI
   ↓
FastAPI
   ↓
Coordinator Agent
   ↓
Intent Detection
   ↓
Select Agent
   ↓
LangChain Retrieval
   ↓
FAISS
   ↓
LLM (Gemini)
   ↓
Generate Response
   ↓
Memory Update
   ↓
Return Response
```

Step explanation:

- **Next.js UI** — the student submits a question through the chat interface.
- **FastAPI** — the backend receives the request and forwards it to the AI service.
- **Coordinator Agent** — entry node of the LangGraph state machine.
- **Intent Detection** — classifies the intent (admission, examination, FAQ).
- **Select Agent** — routes the request to the matching specialist agent.
- **LangChain Retrieval** — retrieves relevant context from the knowledge base.
- **FAISS** — vector search over indexed documents.
- **LLM (Gemini)** — generates the answer grounded in retrieved context.
- **Generate Response** — final answer with sources when available.
- **Memory Update** — conversation history is persisted for continuity.
- **Return Response** — the answer is sent back through FastAPI to the UI.

---

## AI Behaviour Rules

- **Never hallucinate.** Answers must always be grounded in retrieved knowledge.
- **Always retrieve knowledge from RAG before answering.**
- If information is unavailable, **clearly say so** instead of guessing.
- Recommend contacting the appropriate university department when necessary.
- Always explain the next step or university process after the answer.
- Maintain a **professional tone** at all times.
- Keep answers **concise but complete**.

---

## AI Development Rules

Before generating any code:

- **Always read PROJECT_RULES.md first.**
- Read relevant documentation inside `docs/`.
- **Search the existing codebase before creating new files.**
- Reuse existing components, services, utilities, and agents whenever possible.
- **Never duplicate business logic.**
- Never create duplicate folders.
- **Never overwrite existing code unless explicitly requested.**
- Keep architecture consistent.
- Follow **Clean Architecture**.
- Follow **LangChain and LangGraph best practices**.
- Generate **production-ready** code only.
- Prefer updating existing files over creating new ones.
- Keep files small, modular, and reusable.

---

## Code Generation Policy

Before generating any code:

1. Read PROJECT_RULES.md first.
2. Read relevant documentation inside `docs/`.
3. Search existing files before creating new ones.
4. Reuse existing components.
5. Reuse existing services.
6. Reuse existing utilities.
7. Avoid duplicate logic.
8. Prefer updating existing files.
9. Follow existing folder structure.
10. Generate production-ready code only.
11. Never create unnecessary files.
12. Never create unnecessary folders.
13. Never overwrite existing code unless explicitly requested.
14. Maintain consistency across the project.

---

## Prompt Engineering Rules

- **Never hardcode prompts inside routes** — prompts belong in the AI layer, not in API code.
- Store prompts inside `ai/prompts/`.
- **Every agent owns its own prompt.**
- **Reusable prompts only** — shared prompt components over duplicated text.
- **Version prompts** — track prompt changes like code.
- Prefer **structured output** (schemas/JSON) over free-form text.
- **Optimize prompts for accuracy** — test and refine.
- **Keep prompts modular** — compose small prompts instead of one large block.

---

## System Architecture

```
Student
   ↓
Next.js Frontend
   ↓
FastAPI Backend
   ↓
LangGraph Coordinator
   ↓
Admission Agent / Examination Agent / FAQ Agent
   ↓
LangChain RAG
   ↓
FAISS
   ↓
SQLite
   ↓
Final Response
```

The vector index (FAISS) and chat history persist in the database — SQLite during development, PostgreSQL in production.

---

## Project Folder Structure

Every folder has a clear owner and responsibility. All new code must land in the correct folder — do not create parallel or duplicate structures.

| Folder         | Ownership                                                                     |
| -------------- | ----------------------------------------------------------------------------- |
| `frontend/`  | UI only — Next.js pages, components, hooks, types, styling                   |
| `backend/`   | API and business logic — routes, schemas, services, models, middleware       |
| `ai/`        | Agents, LangChain, LangGraph, RAG — agents, chains, tools, memory, retrieval |
| `database/`  | Schema, migrations, seeds                                                     |
| `knowledge/` | University documents and FAQs (source files for RAG)                          |
| `docs/`      | Architecture and documentation                                                |
| `docker/`    | Deployment configuration                                                      |
| `scripts/`   | Automation scripts — setup, seed, maintenance                                |

### Standard Project Layout

```
project-root/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   ├── types/
│   └── public/
│
├── backend/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── middleware/
│   └── main.py
│
├── ai/
│   ├── agents/
│   ├── graphs/
│   ├── rag/
│   ├── memory/
│   ├── prompts/
│   ├── tools/
│   └── utils/
│
├── knowledge/
│   ├── admission/
│   ├── examination/
│   ├── faq/
│   ├── documents/
│   └── vectorstore/
│
├── database/
├── docs/
├── docker/
├── scripts/
├── .env.example
├── docker-compose.yml
├── README.md
└── PROJECT_RULES.md
```

This is the **standard project layout** — every new file must follow this structure.

---

## Performance & Security Standards

**Performance:**

- Lazy loading for non-critical UI.
- Code splitting for route-level bundles.
- API optimization — query only what is needed, paginate large lists.
- Caching where appropriate (static content, knowledge retrieval).

**Security:**

- JWT Authentication for all protected routes.
- Input validation on client and server.
- SQL Injection prevention — always use parameterized queries / ORM.
- XSS protection — escape output, avoid unsafe HTML injection.
- Secure API endpoints — protect sensitive routes by role.
- Environment variables only — never hardcode secrets.

---

## Logging & Monitoring

Log:

- Incoming request.
- User ID (if authenticated).
- Coordinator Agent routing.
- Selected Agent.
- Retrieval execution.
- LLM response time.
- API execution time.
- Errors.
- Exceptions.
- System warnings.

Rules:

- **Never log secrets.**
- **Never log API keys.**
- **Never expose sensitive information.**

---

## Error Handling Standards

- **Friendly error messages** — user-facing errors are clear and actionable.
- **Centralized exception handling** — handle errors in one place, consistently.
- **Proper HTTP status codes** — correct codes for every error type.
- **Fallback responses** — graceful degradation when a service fails.
- **Never expose stack traces** to the client.
- **Log internal errors only** — full details stay in server logs.
- **Retry transient failures when appropriate** — network and rate-limit retries.

---

## Documentation Rules

- Every generated code must follow **PROJECT_RULES.md** (this document).
- **Always read the documentation inside `docs/` before generating code** — architecture and design documents take priority.
- **Never create duplicate files.**
- **Never create unnecessary folders.**
- **Always reuse existing components** and utilities.

**Documentation standards:**

- Every new feature must be documented.
- Every API must be documented (endpoints, schemas, error responses).
- Every AI Agent must have its own documentation.
- Every folder should contain only relevant files.
- Never create duplicate documentation.

---

## Important

**PROJECT_RULES.md is the single source of truth for this project.**

All generated code, architecture, UI, backend services, AI agents, APIs, database changes, and documentation must follow this file. No code should violate these rules.

This file is the permanent development guide and must be followed throughout the project lifecycle. Any code that violates these rules must be corrected before it is accepted.

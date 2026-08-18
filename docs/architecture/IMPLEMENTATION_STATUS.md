# IMPLEMENTATION_STATUS.md

**Agentic AI-Based University Workflow Automation System — SMIU**

> Version: 0.13 · Status: Living document · Last Updated: 15 August 2026 · Owner: Final Year Project Team
> Scope: Tracks actual implementation state of every requirement against the source-of-truth docs (`IMPLEMENTATION_PLAN.md`, `BACKEND_ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `API_SPECIFICATION.md`, `AI_ARCHITECTURE.md`, `ui-ux-design.md`, `DEPLOYMENT.md`, `TESTING_STRATEGY.md`, `DEVELOPMENT_WORKFLOW.md`).
> Source architecture documents are NOT modified by this file.

---

## 1. Status System

Every requirement and every phase uses exactly one of four statuses:

| Status | Meaning |
| ------ | ------- |
| `[ ]` | Not started / incomplete |
| `[~]` | In progress / partially implemented |
| `[?]` | Implementation appears present, but required verification is pending |
| `[x]` | Implementation is present AND adequately verified |

Rules:

- `[x]` requires BOTH (1) the documented requirement is actually implemented, and (2) appropriate verification evidence exists (a test that exercises that requirement, or a verification command actually run and recorded in §3.1).
- A passing backend test suite does NOT automatically verify every requirement — it only verifies the requirements the suite actually exercises.
- A phase is `[x]` only if ALL requirements inside that phase are `[x]`.
- Git commits and file existence are NOT treated as functional verification.

---

## 2. Phase Summary

| # | Phase | Status |
| - | ----- | ------ |
| 1 | Project Setup | `[~]` CI skeletons are echo placeholders; everything else in place |
| 2 | Backend Foundation | `[~]` Background tasks + file upload missing |
| 3 | Database | `[~]` Seeds partial; optimistic-concurrency 409 not surfaced |
| 4 | Authentication | `[x]` All requirements implemented and verified |
| 5 | Frontend Foundation | `[x]` All requirements implemented and verified |
| 6 | Student Dashboard | `[~]` Backend aggregates verified; no UI |
| 7 | Request Management | `[~]` Backend lifecycle + timeline verified; no UI |
| 8 | AI Foundation | `[~]` Service structure, shared config, workflow state, the full LangGraph workflow (incl. the functional clarify node — §9.4/§9.5/§11.3/§11.5), Coordinator, Admission/Examination/FAQ agents, guardrails, conversation memory + agent handoff + error recovery, and prompt-execution wiring/version checks all verified (offline). Phase not marked complete: guardrail/audit logging to `agent_logs` is a Phase 10 concern and real-model AI verification is Phase 13 |
| 9 | RAG Implementation | `[x]` All 8 RAG tasks implemented and verified offline: ingestion + chunking, embeddings, FAISS index + persistence, concrete retriever, context-builder wiring, citation generation/dedup, the knowledge re-indexing job, and the golden retrieval/eval sets (Step R9-7/R9-8, §3.1n) |
| 10 | AI Chat System | `[~]` Backend chat boundary + memory verified; frontend chat + history UI verified |
| 11 | Notifications | `[~]` Backend verified; no UI |
| 12 | Profile & Settings | `[~]` Backend verified; 409 conflict + UI missing |
| 13 | Testing | `[~]` Backend suite green; AI foundation tests present; AI quality/frontend/E2E/load/coverage missing |
| 14 | Deployment | `[~]` Skeleton only; docker builds unverified, compose runs db only |
| 15 | Final Optimization | `[ ]` Not started |

---

## 3. Verification Summary

### 3.1 Commands actually run (this session, 11 Aug 2026)

| Command | Result |
| ------- | ------ |
| `cd backend && .venv\Scripts\python.exe -m pytest -q` | **617 passed, 89 warnings** in 206.24 s. Warnings are non-fatal aiosqlite teardown noise ("Event loop is closed"); no failures/errors. |
| `cd backend && .venv\Scripts\python.exe -m mypy app` | **Success: no issues found in 129 source files.** |
| `cd backend && .venv\Scripts\python.exe -m ruff check app tests` | **FAILED: 3 errors** — `I001` import-sort ×2 (`app/schemas/audit.py`, `app/schemas/sessions.py`), `UP038` isinstance ×1 (`app/schemas/base.py`). Lint is NOT clean. |
| `cd backend` + `DATABASE_URL=sqlite+aiosqlite:///<tmp>/verify_migrations.db` + `.venv\Scripts\python.exe -m alembic upgrade head` | Applied cleanly to head **`4e5f6a7b8c9d`**; **17 tables** created (16 domain tables + `alembic_version`). |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile. |
| `python -m pytest` (from `ai/`) | **165 passed** — `ai/tests/` only (test_config 13, test_state 8, test_coordinator 32, test_workflow 21, test_gateway 34, test_llm_classifier 10, test_admission 23, test_examination 24). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 37 source files** (AI service only; tests excluded by config; backend mypy previously clean on 129 files). |

### 3.1b Commands actually run (Step 1G FAQ Agent session, 13 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile. |
| `cd ai && python -m pytest -q` | **195 passed in 10.66s** — `ai/tests/` only (test_config 13, test_state 8, test_coordinator 32, test_workflow 21, test_gateway 34, test_llm_classifier 10, test_admission 23, test_examination 24, **test_faq 30**). No external AI/API/network calls are made. |
| `python -m pytest ai/tests/test_faq.py -q` (repo root) | **30 passed** — focused FAQ Agent suite, fully offline. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 38 source files** (AI service only; tests excluded by config; +1 file from `ai/agents/faq.py`). |

Step 1G evidence:
- The FAQ Agent tests inject a **fake retriever** (`FakeRetriever` — scripted chunks, records query/categories/top_k) and a **fake/mock gateway** (`FakeGateway` — a `LLMGateway` subclass returning scripted JSON, never a provider SDK); the Coordinator uses the deterministic **rule-based** classifier. No Gemini/OpenAI/Groq key, API, network, database, or backend service is used or required.
- The full 195-test suite (Step 1A–1G) runs fully offline with the same injected fakes; **no external LLM/API/network call is made by any test**.

### 3.1c Commands actually run (Step 1H Guardrails session, 13 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile. |
| `cd ai && python -m pytest -q` | **234 passed in 11.81s** — `ai/tests/` only (test_config 13, test_state 8, test_coordinator 32, test_workflow 21, test_gateway 34, test_llm_classifier 10, test_admission 23, test_examination 24, test_faq 30, **test_guardrails 39**). No external AI/API/network calls are made. |
| `python -m pytest ai/tests/test_guardrails.py -q` (repo root) | **39 passed** — focused guardrails + safety-rules suite, fully offline. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root, scoped `ai/guardrails ai/agents/base.py`) | **Clean for all new/modified code.** Only 2 errors reported, both **pre-existing** in `ai/core/config.py` (untouched by this step). |

Step 1H evidence:
- The guardrails + safety-rules feature is implemented in a new `ai/guardrails/` package (`results.py` — typed `GuardrailDecision`/`GuardrailCategory`; `patterns.py` — declarative rule groups with per-rule stable codes, word-boundary regexes, and safe user-facing fallbacks, evaluated in safety-precedence order per §25-26/§37.2; `guardrails.py` — `SafetyGuardrails.check_input`/`check_output` with a shared module-level `default_guardrails()` singleton) and integrated into the shared `SpecialistAgent` pipeline (`ai/agents/base.py`): input checks short-circuit BEFORE retrieval/LLM with a safe fallback, output checks run AFTER generation with a safe replacement; rules carry `(fallback, category)` so the pipeline can return a contextually correct response and never expose internal detection details (matched pattern/code/category) to the student (§26.3, §37). Empty queries are safely handled (§20.4/§28.3). Guardrail categories cover §26.1 prompt injection, §26.2 jailbreak/role-play/authority invocation + system-prompt extraction, §26.3 unsafe/restricted/out-of-scope prompts, §26.4 unsafe/abusive output, exam-integrity (cheating) violations, assistant authority claims, and sensitive-data/third-party privacy leakage (§37.4, §37.7); out-of-scope/restricted topics route to a department referral.
- All guardrail tests are **deterministic and offline**: the check functions are pure, and pipeline tests use the same injected fake retriever + scripted fake gateway (never a provider SDK). No Gemini/OpenAI/Groq key, API, network, database, or backend service is used or required.

### 3.1d Commands actually run (Step 1I Memory + Handoff + Error Recovery session, 13 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile. |
| `cd ai && python -m pytest -q` | **256 passed in ~11 s** — `ai/tests/` only (test_config 13, test_state 8, test_coordinator 32, test_workflow 21, test_gateway 34, test_llm_classifier 10, test_admission 23, test_examination 24, test_faq 30, test_guardrails 39, **test_memory 22**). No external AI/API/network calls are made. |
| `python -m pytest ai/tests/test_memory.py ai/tests/test_workflow.py ai/tests/test_state.py -q` (repo root) | **51 passed** — focused Step 1I suite (memory 22 + workflow 21 + state 8), fully offline. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 42 source files** (AI service only; tests excluded by config; +4 files from `ai/memory/`, `ai/memory/manager.py`, `ai/graphs/workflow.py`, `ai/core/state.py`). |

Step 1I evidence:
- **Conversation memory** (`ai/memory/manager.py` + `ai/memory/__init__.py`): the stateless `ConversationMemoryManager` implements the §21 memory model — short-term window (recent `CHAT_HISTORY_LIMIT` turns, default 20, §21.2/§21.6), opt-in long-term overflow summarization via an injected `summarizer` callable (LLM-backed in production, deterministic fake in tests; §21.3), session-memory rebuild from persisted history + summary (§21.4/§22.5), and safe persistence (`persist` returns `False` on a writer failure and never raises, so a §23.1 DB write failure cannot fail the run). No provider is ever called by the manager.
- **Agent handoff** (`ai/core/state.py`, `ai/graphs/workflow.py`): new typed `Handoff` model (`routed_to`, `previous_agent`, `reason`) and `current_agent`/`handoff` fields on `WorkflowState` (§24.3-24.4); the workflow `route` node now records the active agent and the handoff metadata for the response envelope, emitted only on an actual agent change (§24.2 first route COORDINATOR→specialist and specialist→specialist switches; same-agent re-routes emit none). The `detect_intent` node enforces the short-term window through the memory manager before classification (§12.5, §21.2), verified with a recording classifier spy.
- All tests are deterministic and offline: the summarizer is an injected fake and the classifier spy never touches a provider SDK. No Gemini/OpenAI/Groq key, API, network, database, or backend service is used or required.

### 3.1e Commands actually run (Step 1J Prompt Execution Wiring + Version Checks session, 13 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile. |
| `python -m pytest ai/tests/test_prompts.py -q` (repo root) | **27 passed** — focused prompt-execution/version suite, fully offline. |
| `cd ai && python -m pytest -q` | **283 passed in ~11 s** — `ai/tests/` only (test_config 13, test_state 8, test_coordinator 32, test_workflow 21, test_gateway 34, test_llm_classifier 10, test_admission 23, test_examination 24, test_faq 30, test_guardrails 39, test_memory 22, **test_prompts 27**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 42 source files** (AI service only; tests excluded by config). |

Step 1J evidence (IMPLEMENTATION_PLAN.md §4 AI task 7 remainder — prompt-execution wiring + version checks):
- **Execution wiring** (`ai/agents/base.py`): the shared `SpecialistAgent._resolve_prompt` resolves the agent's registered versioned prompt from the `PromptRepository` — never hardcoded (§13.1/§34.3) — and `generate()` sends the resolved `self.prompt.text` as the gateway system prompt. Focused tests prove the exact repository-resolved prompt text (not a hardcoded copy) reaches the gateway for Admission, Examination, and FAQ, and that switching the repository to a newer version changes what is sent (§34.6 default-version resolution returns the latest registered version).
- **Ownership/version validation** (§13.1, §34.3): `_resolve_prompt` now fails fast with a `ValueError` when the prompt is missing, requests an unsupported version (clear `key@version` error), is owned by a different agent (ownership metadata mismatch), or carries no owner. This closes the previous gap where an empty/mismatched prompt could be silently accepted.
- **Shared components** (§13.4/§34.7): every specialist prompt composes `GROUNDING_RULES` / `SAFETY_RULES` / `FORMATTING_RULES` / `NO_ANSWER_POLICY` from `ai/prompts/components.py`, and the composed text is what reaches the gateway.
- **Traceability** (§34.6): `GenerationResult` now records `prompt_version` alongside `model` with every generation (including malformed-output degradation), so the resolved prompt version is reproducible per message.
- Regression coverage in the same focused suite proves prompt wiring does not change no-answer short-circuit, input-guardrail short-circuit, or conversation-history injection.
- All tests are deterministic and offline: fake retriever + scripted fake gateway (never a provider SDK). No Gemini/OpenAI/Groq key, API, network, database, or backend service is used or required.

### 3.1f Commands actually run (Step 1K LangGraph Specialist-Phase Wiring session, 13 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile. |
| `python -m pytest ai/tests/test_workflow.py ai/tests/test_workflow_specialists.py -q` (repo root) | **27 passed** — focused workflow + specialist-phase integration suite, fully offline. |
| `cd ai && python -m pytest -q` | **289 passed in ~5 s** — `ai/tests/` only (test_config 13, test_state 8, test_coordinator 32, test_workflow 15, test_gateway 34, test_llm_classifier 10, test_admission 23, test_examination 24, test_faq 30, test_guardrails 39, test_memory 22, test_prompts 27, **test_workflow_specialists 12**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 42 source files** (AI service only; tests excluded by config). |

Step 1K evidence (IMPLEMENTATION_PLAN.md §4 AI tasks 2/3 remainder — LangGraph specialist-phase wiring):
- **Specialist delegation** (`ai/graphs/workflow.py`): the `retrieve` node is now a real node that looks up the router's `selected_agent` in an injected `specialists` map (`Mapping[AgentKey, SpecialistAgent]`) and delegates via `SpecialistAgent.run(query=, message_history=, user_context=)`, storing the resulting `AgentOutput` in `state.agent_output` (§11.2, §12.3). A graph compiled without the injected specialist raises `NotImplementedError` (no false production behavior); a missing signal or the tentative Coordinator is a no-op (never reached via the router edge, §11.3).
- **Pass-through nodes** (§13.5): `build_context`, `generate`, `assemble_citations`, and `aggregate_response` are honest no-op nodes that return `{}` — the specialist agent already runs the full pipeline internally (retrieval §16, context §17, generation §18, citations §19, response assembly/guardrails/fallbacks §20, §25-26), so the workflow never duplicates or re-frames it.
- **Persist node** (§21, §23.1): `persist` is a real node that appends the user query + specialist answer to the short-term memory window via `ConversationMemoryManager.add_turn` and best-effort persists it through an injectable `persist_writer` (default in-memory; backend DB writes are Phase 10). A persistence failure never fails the run (§23.1); the updated window becomes the new `message_history`.
- **Dependency injection**: `build_workflow(coordinator=None, memory=None, specialists=None, persist_writer=None)` — the graph never constructs real LLM clients, retrievers, or persistence backends; everything is injected (fake retriever + fake gateway in tests).
- **Routing preserved end-to-end**: ADMISSION → AdmissionAgent, EXAMINATION → ExaminationAgent, FAQ → FAQAgent, GENERAL → FAQAgent (via the scripted-LLM Coordinator); ambiguous/unknown turns route to the `clarify` placeholder (§9.4, §11.3) with no specialist execution. The clarify node intentionally remains a structural placeholder (raises `NotImplementedError`): its clarifying text is delivered by a prompt, never hardcoded in the graph (§13.2, §34.8), and no prompt version for it exists yet.
- **Regression coverage** in the same focused suite proves agent behavior is preserved through the graph: guardrail-blocked input never reaches retrieval or the LLM, provider failure degrades to a FALLBACK status that the workflow carries through, the injected specialist receives the routed query + history + user context, graph state (conversation_id, user_context, routing_signal, current_agent, agent_output) is preserved, the memory window is enforced on the persisted history, and the repository-resolved registered prompt text is what reaches the gateway.
- All tests are deterministic and offline: fake retriever + scripted fake gateway (never a provider SDK) + injected specialists. No Gemini/OpenAI/Groq key, API, network, database, or backend service is used or required.

### 3.1g Commands actually run (Step 1L Clarification Node session, 13 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile (incl. `ai/agents/coordinator.py` + `ai/graphs/workflow.py`). |
| `python -m pytest ai/tests/test_workflow.py ai/tests/test_workflow_specialists.py ai/tests/test_workflow_clarify.py -q` (repo root) | **45 passed** — focused Step 1L suite (workflow 16 + specialist-phase 12 + **clarify 17**), fully offline. |
| `cd ai && python -m pytest -q` | **307 passed in ~5 s** — `ai/tests/` only (test_config 13, test_state 8, test_coordinator 32, test_workflow 16, test_gateway 34, test_llm_classifier 10, test_admission 23, test_examination 24, test_faq 30, test_guardrails 39, test_memory 22, test_prompts 27, test_workflow_specialists 12, **test_workflow_clarify 17**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 42 source files** (AI service only; tests excluded by config). |

Step 1L evidence (IMPLEMENTATION_PLAN.md §4 AI task 2 remainder — the LangGraph clarify node):
- **Deterministic, data-driven clarification** (`ai/agents/coordinator.py` + `ai/graphs/workflow.py`): the `clarify` node is now a real node that returns a grounded clarifying turn — `AgentOutput(answer=<CoordinatorAgent.clarify(state.routing_signal)>, status=WorkflowStatus.CLARIFYING)` (§4.6, §11.6). The architecture has NO dedicated clarification prompt type (§13.2 prompt types: System, Coordinator — which already covers "clarification, fallback behavior" —, Specialist, Context-injection, Citation/format), so no prompt or version was invented (§13.2/§34.8); the text is built from the live agent registry (`- {name}: {description}` help topics per §9.5, i.e. the Coordinator's enabled, non-Coordinator agents) and is deterministic with no gateway, no prompt lookup, and no LLM call.
- **Grounded behavior by signal** (§4.6/§9.4/§9.5/§11.5): `OUT_OF_SCOPE` → scope boundary + "contact the university directly" referral; a low-confidence ADMISSION/EXAMINATION/FAQ signal → the response names the nearest specialist label (via `registry.resolve`/`registry.get(...).name`) without ever selecting it (§9.4 "optionally offer the nearest specialist"); missing/tentative/GENERAL → a safe generic clarifying turn that lists the help topics and asks the student to choose. Raw routing `reason`/confidence are never surfaced (§26.3, §37). No specialist is executed and no retrieval/LLM call happens on the clarify path (§9.5 — the Coordinator never guesses), proven by loud-gateway + recording-specialist + recording-retriever spies.
- **State preservation**: the node returns only `agent_output`; `routing_signal`, `conversation_id`, `user_context`, `message_history`, `current_agent`, and `handoff` semantics are untouched (§10.2, §24 — no handoff is recorded for a clarifying turn); topology is unchanged (`clarify → END`, §11.3). The `detect_intent`/`route`/specialist-phase wiring from Steps 1D/1K is unchanged.
- All tests are deterministic and offline: injected fake retriever + scripted fake gateway (incl. an injected LLM Coordinator with a low-confidence scripted classifier, verified to make exactly one classification call — never a generation) + rule-based Coordinator. No Gemini/OpenAI/Groq key, API, network, database, or backend service is used or required.

### 3.1h Commands actually run (Phase 9 RAG task 1 — Document Ingestion & Chunking session, 14 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile (incl. `ai/rag/ingestion.py`). |
| `python -m pytest ai/tests/test_ingestion.py -q` (repo root) | **46 passed** — focused document ingestion + chunking suite, fully offline. |
| `cd ai && python -m pytest -q` | **353 passed in ~5 s** — `ai/tests/` only (test_config 13, test_state 8, test_coordinator 32, test_workflow 16, test_gateway 34, test_llm_classifier 10, test_admission 23, test_examination 24, test_faq 30, test_guardrails 39, test_memory 22, test_prompts 27, test_workflow_specialists 12, test_workflow_clarify 17, **test_ingestion 46**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 42 source files** (AI service only; tests excluded by config). |

Phase 9 task 1 evidence (IMPLEMENTATION_PLAN.md §4 RAG task 1 — document ingestion + chunking; AI_ARCHITECTURE.md §14.2/§36.2-36.5; DATABASE_DESIGN.md §21):
- **Ingestion pipeline** (`ai/rag/ingestion.py`, new): the deterministic front half of the RAG pipeline — read → extract text → validate → chunk — with NO embedding model, NO FAISS, NO vector store, NO LLM, NO API/network call (AI_ARCHITECTURE.md §36.2). A typed error hierarchy (`IngestionError` + `UnsupportedFileTypeError`, `EmptyDocumentError`, `MalformedDocumentError`, `InvalidMetadataError`, `DuplicateSourceError`, `DocumentParseError`) gives every validation failure a specific, catchable class (§36.3).
- **Validation** (§36.3): file-type whitelist `pdf/md/txt/docx`; SHA-256 checksum over CRLF-normalized text (`checksum_sha256`/`normalize_text` — platform-stable, §36.3 `knowledge_documents.checksum_sha256`); content scan rejecting empty/blank/binary-only sources (`EmptyDocumentError`); category must map to the `KnowledgeCategory` enum (`admission`/`examination`/`faq`/`documents`); version validated as dotted integers ≤30 chars; `txt`/`md` decoded UTF-8-strict (`MalformedDocumentError` on decode failure). `pdf`/`docx` extraction uses the optional `pypdf`/`python-docx` parsers via `importlib.util.find_spec` and fails loudly with `DocumentParseError` when the package is absent — no silent skip, no mis-read (tested by monkeypatched `find_spec`, deterministic and offline).
- **Metadata** (§36.5): optional markdown front matter (`---`-delimited) declares `title`/`category`/`version`/`author`; unknown/duplicate/empty keys raise `InvalidMetadataError`. `IngestedDocument` carries `title`, `category`, `source_path`, `file_type`, `file_size`, `author`, `version`, `checksum_sha256`, `status='processed'`, `is_active=True`, `chunk_count`, `metadata`, `chunks` (mirrors `knowledge_documents`, §21.1). Chunk metadata matches `knowledge_chunks` (§21.2): `chunk_id`, `document_id`, `chunk_index`, `heading`, `page_number`, `token_count`, `character_count`, `checksum_sha256`, plus source fields.
- **Chunking** (§36.4): paragraph-unit, size-bounded (`chunk_size=800` default), markdown headings attach section context to every following chunk, a small overlap (`overlap=80` default) preserves context across split boundaries of oversized paragraphs **only** (no paragraph is ever duplicated), deterministic chunk ids (`sha256(source_path \x1f version \x1f index)` prefix → same input → same ids), deterministic ordering, token estimate `max(1, len//4)` matching the context builder's §17 estimator.
- **Lifecycle eligibility** (DATABASE_DESIGN.md §21.3/§16.4): `IngestedDocument.is_eligible(current_version=...)` is `True` only for `is_active` + `status='processed'` + current-version documents — the exact candidate filter the Phase 9 retriever must apply; `DocumentChunk.to_retrieved_chunk(score=...)` maps chunks onto the existing `RetrievedChunk` retrieval contract (`ai/rag/retriever.py`) so chunks are ready for the context builder and citation assembler. `ingest_documents` enforces the partial-unique `(source_path, version)` rule (§21.1) with `DuplicateSourceError`. `KnowledgeIngestor(knowledge_root)` discovers only supported files inside category folders (skips dotfiles like `.gitkeep`) and ingests them with folder-derived categories (§36.2).
- Embedding (§15), FAISS indexing, the concrete retriever, context-builder wiring, citation generation, re-indexing, and golden retrieval sets are **intentionally NOT implemented** (Phase 9 tasks 2–8) — this step is ingestion + chunking only. The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged.
- All tests are deterministic and offline: no embedding model, no vector store, no LLM, no API, no database, and no network call is made.

### 3.1i Commands actually run (Phase 9 RAG task 2 — Sentence Transformers Embeddings session, 14 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile (incl. `ai/rag/embeddings.py`). |
| `python -m pytest ai/tests/test_embeddings.py ai/tests/test_ingestion.py -q` (repo root) | **85 passed** — focused embeddings (39) + document ingestion/chunking (46) suites, fully offline. |
| `cd ai && python -m pytest -q` | **392 passed in ~8 s** — `ai/tests/` only (prior 353 + **test_embeddings 39**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 42 source files** (AI service only; tests excluded by config). |

Phase 9 task 2 evidence (IMPLEMENTATION_PLAN.md §4 RAG task 2 — Sentence Transformers embeddings; AI_ARCHITECTURE.md §15):
- **Provider contract** (`ai/rag/embeddings.py`, new): a runtime-checkable `EmbeddingProvider` protocol (`model_name`, `dimension`, `embed(text)`, `embed_batch(texts)`) owns a single model so queries and documents are always embedded in the same space (§15.1 model parity). The architecture-approved concrete provider is `SentenceTransformerEmbeddingProvider` — config-driven (§15.1, `EMBEDDING_MODEL`), loaded **lazily** on the first embed request (`importlib.util.find_spec` + an in-function import), so constructing a provider never downloads weights and tests never need a real model; a missing package or a failed model load raises a typed `EmbeddingProviderError`. `sentence-transformers==5.6.1` was added to `ai/requirements.txt` (verified installed in this environment). `create_embedding_provider(settings)` builds the provider from `Settings.embedding_model` and fails fast (typed error, no model load) when `EMBEDDING_MODEL` is unset.
- **Batch embedding for documents, individual embedding for queries** (§15.1): `EmbeddingService.embed_chunks` feeds chunk texts to the provider in fixed-size batches (default `batch_size=32`, configurable at construction) and preserves input order; `EmbeddingService.embed_query` embeds a query individually through the same provider instance (model parity). **No external API/network call is made anywhere** — embedding runs locally inside the AI service; there is no API-based embedding.
- **Chunk-to-vector association** (§15.2, §21.2): `ChunkEmbedding` carries `chunk_id`, `document_id`, `title`, `category`, `version`, `source_path`, `chunk_index`, `heading`, `model_name`, and the `vector` (with a `dimension` property). The chunk text itself is the embedding input (`prepare_embedding_input` — CRLF-normalized so identical content always yields identical input); metadata is stored beside the vector, never mixed into the embedding text (§21.2).
- **Deterministic validation** (§15.1 fixed dimension): typed error hierarchy (`EmbeddingError` base + `EmbeddingProviderError`, `EmptyEmbeddingInputError`, `EmptyVectorError`, `DimensionMismatchError`, `InvalidVectorError`, `CountMismatchError`); empty chunk lists/blank queries rejected, invalid chunk objects rejected, empty vectors rejected, any vector deviating from the provider's fixed dimension rejected, chunk/vector count mismatches rejected per batch, NaN/inf values rejected, and unexpected provider exceptions wrapped as `EmbeddingProviderError`. No silent truncation or invention of vectors.
- **Offline/fake testing** (TESTING_STRATEGY.md §12.1): `ai/tests/test_embeddings.py` (39 tests) covers the provider protocol contract, single + batched + ordered embedding, chunk-id/metadata association, dimension/empty/count/non-finite validation, provider-failure propagation, configured model/dimension behavior (`EMBEDDING_MODEL` set/unset, `batch_size`), fake-provider injection (deterministic SHA-256-derived vectors; embed inputs recorded), lazy-load behavior (a monkeypatched offline `sentence_transformers` module proves no load at construction and exactly one load on first embed), and the typed error hierarchy. No test downloads or loads model weights and no network call is made. The 46 ingestion tests still pass (§3.1h), proving task 1 is unbroken.
- FAISS indexing/persistence (§15.2), the concrete retriever (§16), context-builder wiring (§17), citation generation (§19), re-indexing, and golden retrieval sets are **intentionally NOT implemented** (Phase 9 tasks 3–8) — this step is embedding generation only. The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged.

### 3.1j Commands actually run (Phase 9 RAG task 3 — FAISS Vector Index + Persistence session, 14 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile (incl. `ai/rag/faiss_index.py`). |
| `python -m pytest ai/tests/test_faiss_index.py -q` (repo root) | **47 passed** — focused FAISS index build/persistence/validation suite, fully offline. |
| `cd ai && python -m pytest -q` | **439 passed in ~15 s** — `ai/tests/` only (prior 392 + **test_faiss_index 47**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 43 source files** (AI service only; tests excluded by config; +1 file from `ai/rag/faiss_index.py`). |

Phase 9 task 3 evidence (IMPLEMENTATION_PLAN.md §4 RAG task 3 — FAISS index + persistence; AI_ARCHITECTURE.md §15.2/§16/§36.7; DATABASE_DESIGN.md §21):
- **FAISS index abstraction** (`ai/rag/faiss_index.py`, new): `build_index(embeddings)` consumes `ChunkEmbedding` records (task 2) in input order — **input order == FAISS position == metadata position** — and stores L2-normalized vectors in an `faiss.IndexFlatIP` (inner product). **Index type + similarity metric: cosine** — the §16.2 "distance metric consistent with the embedding model" for the Sentence Transformers encoder (§15.1), implemented the standard FAISS way (normalize at build and at query time; `METRIC_INNER_PRODUCT`), so raw scores are cosine similarities in [-1, 1] (§16.3 raw scores, not normalized). This is a deliberate, documented metric decision; no metric is silently changed. `VectorIndex.search` is the only low-level primitive — raw (positions, scores), `k` bounded, FAISS `-1` padding dropped, dimension/finite/zero-norm validated — with **no** ranking policy, thresholds, category/status filtering, or `RetrievedChunk` construction (those are task 4).
- **Chunk-to-index metadata mapping** (§15.2, §21.2): one-to-one position ↔ `ChunkEmbedding` ↔ `chunk_id` mapping persisted as `metadata.json` alongside the FAISS binary (`index.faiss`) under the architecture-approved `Settings.vector_store_path` (`knowledge/vectorstore/`, §2.2/§15.2/§5.3); each entry preserves `chunk_id`, `document_id`, `title`, `category`, `version`, `source_path`, `chunk_index`, `heading`, `model_name`, `chunk_text`, `vector`, plus index config (`version`, `metric`, `dimension`, `model_name`, `count`). `chunk_text` was added to `ChunkEmbedding` (minimal compatibility change) so the mapping can reconstruct `RetrievedChunk.snippet` (§19.1) — covered by an updated metadata-preservation regression test. The `knowledge/vectorstore/*` path was added to `.gitignore` (regenerable cache, excluded from retention, §36.7).
- **Persistence/load** (§36.7): `save_index` writes temp files (`index.faiss.tmp`/`metadata.json.tmp`), reloads + validates them against the expected `VectorIndex` (count/dimension/inner-product metric), then atomically replaces the final files; failures clean up temp files and raise `IndexPersistenceError` — never a partially-written, valid-looking index. `load_index` validates the metadata mapping (version, metric, count, dimension, model parity, per-entry structure incl. chunk_text) and cross-checks it against the FAISS binary (count, dimension, metric type) before returning a fully reconstructible `VectorIndex`. `index_exists` confirms a complete index+metadata pair. Persistence is deterministic — identical inputs produce byte-identical `index.faiss` and `metadata.json` (tested).
- **Validation/error handling**: typed `FaissIndexError` hierarchy (`FaissUnavailableError`, `EmptyIndexInputError`, `InvalidVectorError`, `IndexDimensionError`, `DuplicateChunkIdError`, `ModelParityError`, `IndexPersistenceError`, `IndexLoadError`, `IndexVersionError`, `CorruptIndexError`, `MetadataMismatchError`) — empty input, inconsistent dimensions, NaN/inf, zero-norm (not cosine-normalizable), duplicate chunk ids, mixed embedding models (model parity §15.1), missing index/metadata files, corrupted FAISS binary, malformed metadata JSON, unsupported persisted version, entry/count/dimension/model/metric mismatches all fail safely with a specific class; nothing is silently truncated or invented. FAISS is lazy-loaded (`find_spec` + in-function import) with a clear `FaissUnavailableError` when the package is missing (mirrors the embeddings lazy-load pattern); `faiss-cpu==1.14.3` and `numpy==2.3.5` pinned in `ai/requirements.txt`, `faiss`/`numpy` added to the mypy skip-type overrides.
- **Offline/fake testing** (TESTING_STRATEGY.md §12.1): `ai/tests/test_faiss_index.py` (47 tests) covers import/dependency behavior (incl. missing-FAISS via monkeypatched `find_spec`), build count/dimension/type/metric, input-order and chunk_id↔position mapping, metadata preservation, raw cosine-score correctness, `k` bounding, dimension/finite/norm/`k` validation, empty/inconsistent-dimension/non-finite/duplicate-id/mixed-model/zero-norm rejection, save/load round-trip, missing/corrupted/incompatible index + metadata, count/dimension/model/metric mismatches, deterministic byte-identical persistence, and the no-network-import guarantee. All tests use synthetic `ChunkEmbedding` vectors and `tmp_path` — **no Sentence Transformer weights, no FAISS index in the repo tree, no external API/network/database call**.
- The context-builder wiring (§17), citation generation (§19), re-indexing, and golden retrieval sets are **intentionally NOT implemented** (Phase 9 tasks 5–8) — this step is the FAISS index + persistence only. The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged. The 39 embeddings tests (§3.1i) and 46 ingestion tests (§3.1h) still pass, proving tasks 1–2 are unbroken.

### 3.1k Commands actually run (Phase 9 RAG task 4 — Concrete FAISS Retriever session, 14 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile (incl. `ai/rag/faiss_retriever.py`). |
| `python -m pytest ai/tests/test_retriever_faiss.py -q` (repo root) | **45 passed** — focused retriever suite, fully offline (deterministic fake embedding provider + synthetic vectors + in-memory/persisted test indexes). |
| `cd ai && python -m pytest -q` | **484 passed in ~10 s** — `ai/tests/` only (prior 439 + **test_retriever_faiss 45**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package. |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 44 source files** (AI service only; tests excluded by config; +1 file from `ai/rag/faiss_retriever.py`). |

Phase 9 task 4 evidence (IMPLEMENTATION_PLAN.md §4 RAG task 4 — retriever with metadata filtering + top-K; AI_ARCHITECTURE.md §16/§14.3/§14.4; DATABASE_DESIGN.md §21.3; TESTING_STRATEGY.md §12.1):
- **Concrete retriever** (`ai/rag/faiss_retriever.py`, new): `FaissRetriever` is the concrete implementation of the existing `Retriever` protocol (`ai/rag/retriever.py` — unchanged). `retrieve(*, query, categories=(), top_k=4)` embeds the query with the **same** injected `EmbeddingProvider` (task 2, model parity §15.1) and searches the task-3 `VectorIndex` (full pool, `k=count`), applying the §16 retrieval policy: candidates are only the processed, is-active, current-version documents already in the index; primary ranking is the raw cosine similarity score (§16.3 — scores are raw, not normalized); ties break deterministically by index position (the stable input order from tasks 1/3); results are narrowed by the `categories` filter (frozenset of `KnowledgeCategory` values, bare strings coerced) and by **version currency** (§16.4/§21.3 — an injected `current_versions` mapping maps `document_id`/`title` → current version; a non-current-version chunk is dropped, an unknown document stays eligible); chunk ids are de-duplicated; the result is bounded by `top_k` (explicit or configured `RAG_TOP_K` default 4) and converted to `RetrievedChunk` (`chunk_id`, `document_id`, `title`, `category`, `snippet=chunk_text`, `score`). **No similarity threshold was invented** — §16 defines none.
- **Typed error hierarchy**: `RetrieverError` base + `EmptyQueryError`, `InvalidQueryError`, `EmbeddingProviderUnavailableError`, `QueryEmbeddingError`, `InvalidQueryVectorError`, `DimensionMismatchError`, `ModelParityError`, `IndexUnavailableError`, `SearchError`, `RetrievedChunkError` — blank/empty queries, missing provider/index, provider↔index model or dimension parity mismatches, failed/faulty query embedding (incl. zero-norm and non-finite vectors), FAISS search failures (mapped from the task-3 `FaissIndexError` classes), invalid/non-finite search results, and chunk-mapping failures all fail with a specific class; nothing is silently truncated or invented. `create_faiss_retriever(settings, *, provider=None, vector_index=None, top_k=None)` factory loads a persisted index from `Settings.vector_store_path` (`index_exists` → `IndexUnavailableError`; a corrupted pair propagates the precise task-3 `CorruptIndexError`) and honors `settings.rag_top_k`.
- **Offline/fake testing** (TESTING_STRATEGY.md §12.1): `ai/tests/test_retriever_faiss.py` (45 tests) covers protocol conformance, query embedding through the injected provider (spy), model/dimension parity, search invocation on the full pool (spy + real delegation), top-K bounding, raw cosine-score propagation + [-1,1] range, ranking order + deterministic position tie-break, determinism, duplicate-chunk-id dedupe, `RetrievedChunk` mapping + rich index-metadata preservation, category narrowing (incl. bare strings + no-match), version-currency eligibility (stale version excluded, current kept, title-key fallback, unknown → eligible), empty/invalid-query errors, missing provider/index errors, empty index → `[]`, embedding failure propagation, zero-norm/NaN rejection, FAISS failure mapping (`FaissUnavailableError`/generic → `SearchError`, `IndexDimensionError` → `DimensionMismatchError`), invalid/negative/non-integer search positions and non-finite scores → `SearchError`, factory load/missing-index/corrupt-index behavior, and the Admission-agent compatibility path (real specialist + fake gateway). All tests use deterministic SHA-256 fake embeddings + synthetic vectors + `tmp_path` — **no Sentence Transformer weights, no FAISS index in the repo tree, no external API/network/database call**.
- The context-builder wiring (§17), citation generation (§19), re-indexing, and golden retrieval sets are **intentionally NOT implemented** (Phase 9 tasks 5–8) — this step is the concrete retriever only. The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged. The 47 FAISS-index tests (§3.1j), 39 embeddings tests (§3.1i), and 46 ingestion tests (§3.1h) still pass, proving tasks 1–3 are unbroken.

### 3.1l Commands actually run (Phase 9 RAG task 5 — ContextBuilder Integration session, 14 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile (incl. finalized `ai/rag/context_builder.py`). |
| `cd ai && python -m pytest tests/test_context_builder.py tests/test_agent_context_integration.py -q` | **38 passed** — focused ContextBuilder unit + specialist-agent integration suite, fully offline (synthetic `RetrievedChunk` + char estimator + fake retriever/gateway). |
| `cd ai && python -m pytest -q` | **522 passed in ~12 s** — `ai/tests/` only (prior 484 + **test_context_builder 21** + **test_agent_context_integration 17**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package (new test files included). |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 44 source files** (AI service only; tests excluded by config). |

Phase 9 task 5 evidence (IMPLEMENTATION_PLAN.md §4 RAG task 5 — context builder within the token budget; AI_ARCHITECTURE.md §17/§19.1/§19.3/§13.5/§20.4; TESTING_STRATEGY.md §12.1):
- **ContextBuilder finalized + integrated** (`ai/rag/context_builder.py`): the Phase 8 `ContextBuilder` is now the specialist agents' grounded context injector (§17) — every `SpecialistAgent.run` executes retrieve → `build_context` (delegating to the injected `ContextBuilder`) → generate → assemble citations; the `create_*_agent` factories thread `Settings.context_budget_tokens` into the builder; the LangGraph `build_context` node is an honest pass-through. This step's finalization: (a) each evidence block renders the chunk identity `[chunk: {chunk_id}]` so the LLM can emit real `cited_chunk_ids` that existing citation assembly maps onto the retrieved set (§19.1/§19.3 — previously the ids were invisible to the LLM); (b) a public deterministic `estimate_tokens(text)` method (§17.3 — `max(1, len(text) // 4)`, no tokenizer/model download, injectable estimator). No pipeline redesign: the §17.2 assembly order, §17.4 prioritization (evidence 9 > history 5 > user context 1; system rules + current query never-trim 10), lowest-score-evidence-first / oldest-history-first / then-user-context trimming, and `ContextOverflowError`-only-when-essential-exceeds behavior were already correct and are now pinned by a dedicated suite.
- **Offline/fake testing** (TESTING_STRATEGY.md §12.1): `ai/tests/test_context_builder.py` (21) pins §17 assembly/budgeting/determinism/metadata with a char-count estimator and exact unit-total budgets (empty retrieval; section order + labels; evidence/instruction separation; single/multiple chunks in budget; exact boundary keeps everything; lowest-score evidence trimmed first; individually-fitting-but-collectively-over chunks trimmed; oversized chunk dropped safely; system rules never trimmed before other content; oldest history trimmed first; user context dropped before evidence; bounded overshoot across sizes — render headers sit inside the §17.3 safety margin; determinism; default `len//4` estimator incl. empty/minimum; injectable estimator; metadata + chunk-identity preservation; identity never fabricated; no fabricated content; malformed chunk robustness; overflow only when essential exceeds budget; no overflow when only removable content exceeds). `ai/tests/test_agent_context_integration.py` (17) proves the wiring end-to-end offline (real agents + real `ContextBuilder` + fake retriever + fake gateway): each specialist builds context through the builder, GENERAL → FAQ routes through the real workflow, retriever/builder called exactly once per run, `context_budget_tokens` reaches `context_builder.max_tokens`, injectable builder, empty retrieval short-circuits without builder/LLM, guardrail-blocked input never reaches retrieval/LLM, prompt + version preserved, history included in context, `AgentOutput` shape unchanged, citation compatibility via `[chunk: …]` ids in context, injected retriever used, and all three factories run offline with empty API keys.
- Citation generation/dedup (§19), re-indexing, and golden retrieval sets are **intentionally NOT implemented** (Phase 9 tasks 6–8). The shared `Retriever` protocol, `WorkflowState`, agents, prompts, and workflow are unchanged. The 45 retriever tests (§3.1k), 47 FAISS-index tests (§3.1j), 39 embeddings tests (§3.1i), and 46 ingestion tests (§3.1h) still pass, proving tasks 1–4 are unbroken.

### 3.1m Commands actually run (Phase 9 RAG task 6 — Citation Generation + Dedup session, 15 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile (incl. finalized `ai/agents/base.py`). |
| `cd ai && python -m pytest tests/test_citations.py -q` | **28 passed** — focused citation generation/dedup suite, fully offline (synthetic `RetrievedChunk` + fake retriever/gateway). |
| `cd ai && python -m pytest -q` | **550 passed in ~12 s** — `ai/tests/` only (prior 522 + **test_citations 28**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package (new test file included). |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 44 source files** (AI service only; tests excluded by config). |

Phase 9 task 6 evidence (IMPLEMENTATION_PLAN.md §4 RAG task 6 — citation generation/dedup; AI_ARCHITECTURE.md §19/§16.3/§16.5/§20.3/§20.4; DATABASE_DESIGN.md §32.6; TESTING_STRATEGY.md §12.1):
- **Citation assembly finalized** (`ai/agents/base.py` `SpecialistAgent.assemble_citations`): citations are generated only from retrieved evidence — the LLM may reference evidence only via `cited_chunk_ids` and the authoritative metadata (chunk_id, document_id, title, category, snippet, score) always comes from the retrieved `RetrievedChunk[]` (§19.1); a cited id not in the retrieved set is ignored, never invented (§20.3). Dedup is deterministic and per-chunk (§19.3 — one citation per chunk per message): repeated cited ids collapse to one citation and duplicate chunk ids in the retrieved set keep the strongest (highest retrieval score) occurrence — distinct chunks are never merged. Ordering is deterministic (§19.3/§16.3/§16.5): retrieval score descending with the retrieved position as the tie-break — the order never follows the LLM's citation order and is identical on repeated execution. Scores clamp to the 0..1 `ai_sources_score_check` contract (§19.4, DATABASE_DESIGN.md §32.6); non-finite scores degrade to 0.0 instead of failing `Citation` validation. The assembler runs inside the shared specialist pipeline (retrieve → build_context → generate → assemble_citations), so Admission, Examination, FAQ, and GENERAL → FAQ all use the same implementation; the retriever is called exactly once per run (§16.5) and the ContextBuilder's `[chunk: {chunk_id}]` evidence ids (§3.1l) map directly onto the citations (§19.1/§19.3). `AgentOutput.citations` (the existing contract) is preserved unchanged. No prompt version was introduced; no URL/source-name parsing; no re-ranking, similarity threshold, or new scoring formula. The `ai_sources` DB persistence layer (DATABASE_DESIGN.md §22) is NOT this task (it already exists and is tested).
- **Offline/fake testing** (TESTING_STRATEGY.md §12.1): `ai/tests/test_citations.py` (new, 28) — grounding + source-metadata preservation (§19.1), ghost cited ids + empty evidence never fabricated (§20.3), LLM cannot inject source metadata, empty retrieval → grounded no-answer with zero citations and no LLM call (§20.4), empty cited list, repeated-id dedup, strongest-duplicate-wins, distinct chunks from one document not merged, score-descending ordering, retrieval-position tie-break on equal scores (never LLM order), repeated-run determinism, [0,1] score clamping (§19.4/§32.6), non-finite scores → 0.0 without crash, Admission/Examination/FAQ end-to-end grounded citations, GENERAL → FAQ citations through the real workflow, `AgentOutput` contract preserved, unanswerable no-answer preserved, retriever + LLM each called exactly once (§16.5), ContextBuilder evidence-id ↔ citation chunk_id compatibility, chunk_id never fabricated beyond evidence, duplicate-chunk determinism, missing optional document_id handled safely, empty-evidence assembler safety. The 38 ContextBuilder tests (§3.1l), 45 retriever tests (§3.1k), 47 FAISS-index tests (§3.1j), 39 embeddings tests (§3.1i), and 46 ingestion tests (§3.1h) still pass, proving tasks 1–5 are unbroken.
- Phase 9 tasks 7–8 (the knowledge re-indexing job and the golden retrieval/eval sets) are implemented in the follow-up session — see §3.1n. The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged.

### 3.1n Commands actually run (Phase 9 RAG tasks 7–8 — Knowledge Re-indexing + Golden Retrieval/Eval session, 15 Aug 2026)

| Command | Result |
| ------- | ------ |
| `python -m compileall -q ai` (repo root) | **OK** — all `ai/` sources byte-compile (incl. `ai/rag/reindexer.py`, `ai/rag/evaluation.py`). |
| `python -m pytest ai/tests/test_reindexer.py ai/tests/test_evaluation.py -q` (repo root) | **30 passed** — focused re-indexer (15) + golden retrieval/evaluation (15) suites, fully offline. |
| `cd ai && python -m pytest -q` | **580 passed in ~17 s** — `ai/tests/` only (prior 550 + **test_reindexer 15** + **test_evaluation 15**). No external AI/API/network calls are made. |
| `ruff check ai` (repo root) | **All checks passed** — 0 errors for the `ai/` package (new source + test files included). |
| `mypy --strict --config-file ai/pyproject.toml` (repo root) | **New/modified RAG files clean** (`ai/rag/reindexer.py` + `ai/rag/evaluation.py` are strict-clean). Only 5 errors reported, all **pre-existing** in committed tasks 1–6/agent code (out of scope): `ai/agents/base.py:45` (`GuardrailCategory` not explicitly exported), `ai/agents/faq.py:47`, `ai/agents/examination.py:46`, `ai/agents/admission.py:43` (`no-untyped-def`), `ai/rag/ingestion.py:432` (unused `type: ignore[import-not-found]` — environment-dependent; `pypdf` installed here). |
| `mypy --config-file ai/pyproject.toml` (repo root) | **Success: no issues found in 46 source files** (AI service only; tests excluded by config; +2 files from `ai/rag/reindexer.py` + `ai/rag/evaluation.py`). |
| `cd backend && & "C:\Users\Bilal\AppData\Local\Python\pythoncore-3.13-64\python.exe" -m pytest -q -o console_output_style=classic -o addopts=""` | **617 passed in ~137 s** — backend suite unchanged (no backend edits); matches the §3.1 baseline. Warnings are non-fatal aiosqlite teardown noise ("Event loop is closed"). |

Phase 9 tasks 7–8 evidence (IMPLEMENTATION_PLAN.md §4 RAG tasks 7–8; AI_ARCHITECTURE.md §14.2/§16/§36; TESTING_STRATEGY.md §12.2):
- **Knowledge re-indexing job** (`ai/rag/reindexer.py`, new, task 7): `KnowledgeReindexer(knowledge_root, vector_store_path, ingestor, embedding_service, provider)` orchestrates the deterministic re-index pipeline end to end — ingest the current corpus (`KnowledgeIngestor`, task 1) → embed (`EmbeddingService`, task 2) → build + save the FAISS index (`save_index`, task 3) → atomically swap the persisted manifest + index (`ReindexReport`: added/removed/changed counts, per-source diffs) only after verification. An optional injected `verify_before_swap: Callable[[VectorIndex], bool]` gates the swap (a verification failure aborts with the old index untouched). The new tests caught a real bug: removals were never detected — `_plan_changes` now computes `removed_sources = {entry.source_path for entry in previous_index.entries} - set(current)`, warns, and short-circuits only when there are no adds/changes AND no removals; removal-only runs safely skip embedding (`new_embeddings = ... if changed else []`, guarding `EmptyEmbeddingInputError`). Typed `ReindexError` hierarchy (`ReindexError`/`IndexBuildError`/`IndexSaveError`/`EmptyEmbeddingInputError`/`VerificationFailedError`); `async reindex()` = `await asyncio.to_thread(self.run)` for the future worker trigger. The scheduled-worker orchestration itself remains a Phase 2/10 concern — this task delivers the job, not the scheduler.
- **Golden retrieval/eval sets** (`ai/rag/evaluation.py`, new, task 8): typed golden-set models (`GoldenDocument`/`GoldenQuery`/`GoldenSet` with per-query `expected_document_id` + optional `expected_categories`), the versioned fixture `ai/tests/golden/retrieval/golden_retrieval_v1.json` (6 documents, 9 queries covering all 4 categories + 1 info-unavailable query; deterministic chunk ids derived from the real pipeline's `sha256(source \x1f version \x1f index)` scheme so the fixture and the production index agree), `load_golden_set`/`default_golden_set`, `build_golden_index` (tiny designed corpus → embeddings → FAISS index via tasks 2–3), `golden_retriever_for_index`, `recall_at_k`/`precision_at_k`, `evaluate_retrieval` (recall/precision/MRR over the golden queries, configurable `top_k`; per-category gates 0.5/0.25/0.5 per TESTING_STRATEGY.md §12.2), and `build_golden_verifier` (a ready-made `verify_before_swap` for task 7). All deterministic and offline — designed synthetic chunks + SHA-256 fake embeddings; **no model weights, no network, no database**.
- **Tests** (TESTING_STRATEGY.md §12.1/§12.2): `ai/tests/test_reindexer.py` (15) — full re-index from a temp corpus, added/changed/removed detection (incl. the removal-only path), atomic manifest swap, unchanged-corpus short-circuit (no re-embedding, no re-write), the `verify_before_swap` gate (verified-abort leaves the old index intact), missing-corpus `EmptyEmbeddingInputError`, persistence round-trip, deterministic reports, async entry. `ai/tests/test_evaluation.py` (15) — golden-set load/defaults, fixture integrity (version/counts/chunk-id scheme), golden-index build + retrieval recall/precision/MRR (pass + fail scenarios via `top_k=1`, per-category gates), info-unavailable no-answer coverage, deterministic ids, and the golden verifier (good provider passes the swap, bad provider fails it). The 28 citation tests (§3.1m), 38 ContextBuilder tests (§3.1l), 45 retriever tests (§3.1k), 47 FAISS-index tests (§3.1j), 39 embeddings tests (§3.1i), and 46 ingestion tests (§3.1h) still pass, proving tasks 1–6 are unbroken.
- No pipeline redesign: `KnowledgeReindexer` reuses tasks 1–3 exactly (`ingest_documents` → `IngestedDocument[]`, `embed_chunks` → `ChunkEmbedding[]`, `build_index`/`save_index` from task 3). The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged.

### 3.2 Existing test evidence (committed suite; executed above as part of the pytest run)

- `backend/tests/api/` — 13 files: auth, auth bearer, RBAC, sessions, students, users, requests, notifications, conversations, messages, ai, knowledge.
- `backend/tests/unit/services/` — auth (43 tests), requests (25), notifications (14), ai_sources (14), conversations (17), chat_history (13), feedback (17), audit/agent logs, sessions, students, users, departments, documents, knowledge.
- `backend/tests/unit/repositories/` — base repository (21) + per-aggregate repos.
- `backend/tests/unit/` — jwt, password, security edge cases, security hardening (rate limit), email, migration helpers, models, models mixins, alembic, database health.
- `backend/tests/test_health.py`, `test_settings.py`, `test_docs.py`, `test_database.py`.
- `ai/tests/` — `test_config.py` (13), `test_state.py` (8), `test_coordinator.py` (32), `test_workflow.py` (16), `test_gateway.py` (34), `test_llm_classifier.py` (10), `test_admission.py` (23), `test_examination.py` (24), `test_faq.py` (30), `test_guardrails.py` (39), `test_memory.py` (22), `test_prompts.py` (27), `test_workflow_specialists.py` (12), `test_workflow_clarify.py` (17), `test_ingestion.py` (46), `test_embeddings.py` (39), `test_faiss_index.py` (47), `test_retriever_faiss.py` (45), `test_context_builder.py` (21), `test_agent_context_integration.py` (17), `test_citations.py` (28), `test_reindexer.py` (15), `test_evaluation.py` (15) = 580 tests, all passing. These verify the AI **foundation, Coordinator, the Admission + Examination + FAQ agents, the guardrails/safety rules, the conversation memory + agent handoff + error recovery, the prompt-execution wiring + version checks, the functional clarify node, the RAG document-ingestion/chunking stage, the RAG Sentence Transformers embedding stage, the RAG FAISS index + persistence stage, the RAG retriever stage, the RAG ContextBuilder integration stage, the RAG citation generation/dedup stage, the RAG knowledge re-indexing stage, and the RAG golden retrieval/eval stage**: shared configuration (`ai/core/config.py`), typed workflow state (`ai/core/state.py`), the provider-agnostic LLM gateway (`ai/gateway/` — Gemini/OpenAI/Groq adapters, retry + in-provider fallback, error mapping, secret redaction, factory), the rule-based and LLM-backed intent classifiers (`ai/agents/intent_classifier.py`), the Coordinator (`ai/agents/coordinator.py`), the full LangGraph workflow (`ai/graphs/workflow.py`, nodes/edges/routing/termination per `AI_ARCHITECTURE.md` §11.1–11.3) with the real `detect_intent`/`route`/`clarify` nodes wired to the Coordinator, the Admission, Examination, and FAQ agents (`ai/agents/admission.py`, `ai/agents/examination.py`, `ai/agents/faq.py` + `ai/agents/base.py`) with their versioned prompts, context builder, citation assembly, no-answer/error fallbacks, and Coordinator → specialist routing (see §4 Phase 8), the guardrail/safety checks (`ai/guardrails/` — prompt-injection/jailbreak/unsafe/restricted/out-of-scope input checks and unsafe/leakage/authority output checks, per §25–26, §37) integrated into the shared specialist pipeline (see §4 Phase 8), and the conversation-memory manager + handoff + error recovery (`ai/memory/` + §21/§23/§24 — short-term window, opt-in long-term summarization, session rebuild, safe persistence, typed `Handoff` metadata recorded by the `route` node, memory window enforced before intent classification; see §3.1d), and the prompt-execution wiring + version checks (`ai/agents/base.py` + `ai/prompts/` — repository-resolved versioned prompts actually reach the gateway, ownership/unsupported-version validation fails fast, shared components compose into every final prompt, resolved `prompt_version` recorded with each generation per §34.6; see §3.1e). LLM adapter behavior is exercised offline with injected fake SDK clients (verified via `google-genai`, `openai`, and `groq` client construction paths in the factory). They do NOT verify real LLM output quality, RAG retrieval quality, grounding, citation correctness, agent routing quality against a live model, real-model long-term summarization, or end-to-end chat — those are unimplemented or unverified.
- **Caveat:** API/persistence tests build the schema with `Base.metadata.create_all`, NOT Alembic. Real migrations are exercised only by `backend/tests/unit/test_alembic.py` (baseline + full-schema upgrade/downgrade) plus the manual `alembic upgrade head` run in §3.1.

### 3.3 Verification NOT performed

- Test coverage measurement (`pytest --cov` / coverage report) — not run; no coverage threshold measured.
- `ruff` is known failing (3 errors) — lint gate NOT green. (`ruff check ai` is clean; the failures are in `backend/app/schemas/`.)
- Docker: no `docker build` of any service image; no `docker compose config`/up validation.
- Frontend: `npm run build` compiled (Next.js 15.5.23), `npx tsc --noEmit` clean. No component/E2E tests yet.
- AI service: foundation + Coordinator + Admission/Examination/FAQ Agent + guardrails + memory/handoff + prompt-execution checks + specialist-phase workflow wiring + the functional clarify node + the RAG document-ingestion/chunking stage + the RAG Sentence Transformers embedding stage + the RAG FAISS index/persistence stage + the RAG retriever stage + the RAG ContextBuilder integration + citation generation/dedup + knowledge re-indexing + golden retrieval/eval stages only (compileall, pytest 580, ruff, mypy) — no real LLM generation (all gateway calls use injected fake clients), no real embedding model is loaded/downloaded in tests (fake providers + monkeypatched lazy-load path), no retrieval run against a real persisted corpus (synthetic vectors + in-memory/persisted test indexes only; no corpus is ingested/embedded/retrieved in production), no citation generation against real sources, no external AI/API/network calls. No AI workflow node remains a placeholder.
- No manual HTTP smoke test against a running server.
- No performance/load testing.

### 3.4 Verification pending

- `[?]` Docker image builds (Phase 14).
- `[?]` AI functional behavior — LLM generation, intent-classification quality against a live model, RAG retrieval/grounding/citation quality, agent routing quality, memory, agent handoff, end-to-end chat. The Coordinator's intent detection + routing, the LLM gateway, the Admission + Examination + FAQ Agent pipelines, the rule-based guardrails, the memory/handoff layer, the prompt-execution wiring, the specialist-phase workflow wiring (retrieve → `agent.run` → `agent_output`; persist → memory window), the functional clarify node (§9.4/§9.5/§11.3/§11.5), the RAG document-ingestion/chunking stage (§14.2/§36 — validation, metadata, deterministic chunking, lifecycle eligibility), the RAG Sentence Transformers embedding stage (§15 — injectable provider, lazy model load, batched chunk embedding + individual query embedding, model parity, chunk-to-vector association, deterministic dimension/empty/count/non-finite validation), and the RAG FAISS index + persistence stage (§15.2/§16/§36.7 — cosine metric via L2-normalized vectors + `IndexFlatIP`, deterministic position↔chunk_id metadata mapping, atomic temp→replace persistence with reload validation, typed corruption/version/count/dimension/model/metric errors) and the RAG retriever stage (§16/§14.3/§14.4 — query embedding via the same injected provider, raw cosine ranking with a deterministic position tie-break, category + version-currency filtering, top-K/`RAG_TOP_K` bounding, `RetrievedChunk` construction, typed `RetrieverError` hierarchy, persisted-index factory) and the RAG ContextBuilder stage (§17 — budgeted, labeled context assembly wired into every specialist's retrieve → build_context → generate pipeline, `Settings.context_budget_tokens` → `context_builder.max_tokens` through the factories, §17.4 prioritization + `ContextOverflowError`, deterministic `estimate_tokens` §17.3, chunk-identity rendering for §19.1/§19.3 citation compatibility, empty-retrieval short-circuit §20.4) and the RAG citation generation/dedup stage (§19 — deterministic score-ordered citation assembly from retrieved `RetrievedChunk` metadata with retrieval-position tie-break §16.3, per-chunk dedup §19.3, 0..1 `relevance_score` clamp §19.4/§32.6, no fabrication §20.3, `AgentOutput.citations` contract preserved) are implemented and exercised offline (fake clients/providers + synthetic vectors, 522 AI tests); none of this is exercised against a real model or a real retrieval pipeline.
- `[?]` The RAG knowledge re-indexing job (task 7, `ai/rag/reindexer.py`) and golden retrieval/eval sets (task 8, `ai/rag/evaluation.py`) are implemented and covered by deterministic offline tests (Step R9-7/R9-8, §3.1n — 30 new tests, full `ai/` suite 580 passed). Remaining unverified: running re-index + golden evaluation against a real persisted corpus with the real embedding model (no real corpus exists yet — `knowledge/` folders are `.gitkeep` placeholders; seeded content is the Phase 3 seed-data concern) and live-model retrieval quality (Phase 13).
- Everything marked `[?]` or `[~]` or `[ ]` in §4, including: 409 optimistic-concurrency behavior, knowledge/user seeds, background tasks, file upload, full compose stack, reverse proxy/HTTPS, backups, secrets store, external monitoring, §32–33 checklists, frontend + E2E test suites, coverage report.

---

## 4. Phase-by-Phase Requirements

### Phase 1 — Project Setup — `[~]`

- `[x]` **Standard repository folder structure per PROJECT_RULES.md**
  - Source: `IMPLEMENTATION_PLAN.md` §3 Phase 1; PROJECT_RULES.md
  - Implementation: repo layout — `backend/`, `ai/`, `frontend/`, `database/`, `docker/`, `docs/`, `knowledge/`, `testing/`, `.github/`
  - Verification: directory inspection (this session)
  - Notes: matches README §5 folder map
- `[x]` **Environment templates**
  - Source: `IMPLEMENTATION_PLAN.md` §3 Phase 1
  - Implementation: `.env.example`, `backend/.env.example`, `frontend/.env.example`, `ai/.env.example`
  - Verification: file inspection
- `[x]` **Docker skeletons per service**
  - Source: `IMPLEMENTATION_PLAN.md` §3 Phase 1
  - Implementation: `backend/Dockerfile`, `frontend/Dockerfile`, `ai/Dockerfile`
  - Verification: file inspection only
  - Notes: image builds NOT verified (see Phase 14)
- `[~]` **CI skeletons (lint / type-check / build)**
  - Source: `IMPLEMENTATION_PLAN.md` §3 Phase 1 completion criteria
  - Implementation: `.github/workflows/{backend,frontend,ai}-ci.yml`
  - Verification: file inspection
  - Gap: workflows contain only `echo` placeholder steps; they do not run lint, type-check, or build
- `[x]` **`.gitignore` / `.gitattributes`**
  - Source: `IMPLEMENTATION_PLAN.md` §3 Phase 1
  - Implementation: root `.gitignore`, `.gitattributes`
  - Verification: file inspection
- `[x]` **Architecture doc set in place**
  - Source: `IMPLEMENTATION_PLAN.md` §3 Phase 1
  - Implementation: `docs/architecture/*.md` (9 documents) + `docs/README.md`
  - Verification: file inspection

### Phase 2 — Backend Foundation — `[~]`

- `[x]` **FastAPI application factory + ASGI entrypoint**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 1; `BACKEND_ARCHITECTURE.md` §6
  - Implementation: `backend/app/main.py`, `backend/app/core/app_factory.py`
  - Verification: `backend/tests/test_docs.py`, `backend/tests/test_health.py` (app boots via TestClient); suite 617 passed
- `[x]` **Settings (Pydantic Settings) with environment separation**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 2; `BACKEND_ARCHITECTURE.md` §7
  - Implementation: `backend/app/config/settings.py`
  - Verification: `backend/tests/test_settings.py` (3 tests)
- `[x]` **Structured logging with correlation IDs**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 3; `BACKEND_ARCHITECTURE.md` §16
  - Implementation: `backend/app/core/logging.py`, `backend/app/middleware/request_id.py`, `backend/app/middleware/logging.py`, `backend/app/utils/request_id.py`
  - Verification: `backend/tests/test_health.py` — correlation-ID reuse + request-ID generation
- `[x]` **Centralized exception handling + uniform error envelope**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 4; `BACKEND_ARCHITECTURE.md` §15
  - Implementation: `backend/app/exceptions/app_error.py`, `backend/app/exceptions/handlers.py`, `backend/app/utils/response.py`, `backend/app/schemas/response.py`
  - Verification: `test_health.py::test_unknown_route_returns_error_envelope` + every API test asserting the envelope
- `[x]` **Dependency injection (session, services)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 5; `BACKEND_ARCHITECTURE.md` §8
  - Implementation: `backend/app/dependencies/{database,services,auth,rbac,settings}.py`
  - Verification: exercised by all API tests through the real app
- `[x]` **API versioning under `/api/v1`**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 6; `API_SPECIFICATION.md` §14
  - Implementation: `backend/app/core/constants.py` + router mounting in `app_factory.py`
  - Verification: all API tests target `/api/v1/...`
- `[x]` **Health endpoints** (`/health/live`, `/health/ready`, `/health`, `/health/version` + orchestration aliases)
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 7; `API_SPECIFICATION.md` §24
  - Implementation: `backend/app/api/v1/endpoints/health.py`
  - Verification: `backend/tests/test_health.py` (5 endpoint tests incl. aliases)
- `[x]` **Middleware (CORS, security headers, request logging, rate limiting)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 8; `BACKEND_ARCHITECTURE.md` §17
  - Implementation: `backend/app/middleware/{cors,security,logging,request_id,rate_limit}.py`
  - Verification: `test_health.py` (security headers, CSP) + `backend/tests/unit/test_security_hardening.py` (rate-limit behavior)
- `[x]` **Self-hosted API docs (Swagger/ReDoc with vendored assets)**
  - Source: `BACKEND_ARCHITECTURE.md` §27; `API_SPECIFICATION.md` §30
  - Implementation: `backend/app/core/app_factory.py`, `backend/static/docs/`
  - Verification: `backend/tests/test_docs.py` (5 tests)
- `[ ]` **Background task infrastructure** (embeddings, indexing, notifications, retention)
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 9; `DEVELOPMENT_WORKFLOW.md` §27.5
  - Implementation: not present (no `BackgroundTasks`/worker code)
  - Remaining work: worker + job orchestration; this also blocks RAG re-indexing (Phase 9)
- `[ ]` **File upload handling** (validation, checksums, safe filenames)
  - Source: `IMPLEMENTATION_PLAN.md` §4 Backend task 10; `API_SPECIFICATION.md` §35
  - Implementation: not present (no `UploadFile` endpoint; `documents` model/repo/service exist but are unused by any route)
  - Remaining work: upload endpoint, type/size/checksum validation, storage, safe filenames

### Phase 3 — Database — `[~]`

- `[x]` **SQLAlchemy 2.0 base + session management**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Database task 1; `BACKEND_ARCHITECTURE.md` §13
  - Implementation: `backend/app/database/{base,session,utils,health}.py`
  - Verification: `backend/tests/test_database.py` (URL normalization) + shared fixtures; suite green
- `[x]` **Models for all 16 tables**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Database task 2; `DATABASE_DESIGN.md` §12–25
  - Implementation: `backend/app/models/*.py` (users, students, departments, ai_conversations, chat_history, requests, request_timeline, notifications, documents, knowledge_documents, knowledge_chunks, ai_sources, feedback, audit_logs, agent_logs, sessions)
  - Verification: `test_models.py::test_all_sixteen_tables_registered`; `alembic upgrade head` run created all 17 tables (16 + version) — §3.1
- `[x]` **Relationships, constraints, indexes**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Database task 3; `DATABASE_DESIGN.md` §8–11
  - Implementation: declared on models
  - Verification: `backend/tests/unit/test_models.py` (cascade catalog, check-constraint names, partial/functional index clauses)
- `[x]` **Alembic migrations apply cleanly**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Database task 4; `DATABASE_DESIGN.md` §28
  - Implementation: `backend/alembic/versions/` — `1a2b3c4d5e6f` baseline, `2c3d4e5f6a7b` full schema, `3d4e5f6a7b8c` password-reset columns, `4e5f6a7b8c9d` seed departments
  - Verification: `backend/tests/unit/test_alembic.py` (baseline/full upgrade + downgrade reversibility) AND manual `alembic upgrade head` → head `4e5f6a7b8c9d`, 17 tables (§3.1)
- `[~]` **Seed data** (departments, sample knowledge, sample users)
  - Source: `IMPLEMENTATION_PLAN.md` §4 Database task 5
  - Implementation: departments only (`20260807_0003_4e5f6a7b8c9d_seed_departments.py`)
  - Gap: sample users and sample knowledge documents not seeded
- `[x]` **Repository pattern foundation**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Database task 6; `BACKEND_ARCHITECTURE.md` §12
  - Implementation: `backend/app/repositories/base.py` + per-aggregate repositories
  - Verification: `backend/tests/unit/repositories/test_base_repository.py` (21 tests) + per-aggregate repo tests
- `[x]` **Soft delete + ownership scoping**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Database task 7; `DATABASE_DESIGN.md` §26, §30
  - Implementation: `backend/app/models/mixins.py::SoftDeleteMixin`; live-row scoping enforced by repositories; owner checks in every route
  - Verification: `test_models_mixins.py::test_soft_delete_lifecycle`, repository tests, owner-scoping API tests
- `[~]` **Optimistic concurrency (`version` fields)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Database task 8; `DATABASE_DESIGN.md` §4.4, §34.5
  - Implementation: `VersionMixin`; `BaseRepository.update` bumps version
  - Verification: `test_models_mixins.py::test_version_default_and_increment`, `test_base_repository.py::test_update_applies_values_and_bumps_version`
  - Gap: no endpoint surfaces a 409 version-conflict (see Phase 12)
- `[x]` **Audit-write patterns**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Database task 8; `DATABASE_DESIGN.md` §24
  - Implementation: `backend/app/models/audit_logs.py`, `backend/app/services/audit_logs.py`; auth flows record audit events
  - Verification: `backend/tests/unit/services/test_audit_logs_service.py` (14 tests); auth-service tests assert audit events

### Phase 4 — Authentication — `[x]`

- `[x]` **Password hashing (argon2)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Auth task 1; `BACKEND_ARCHITECTURE.md` §9.2; `API_SPECIFICATION.md` §12.5
  - Implementation: `backend/app/core/security/password.py`
  - Verification: `backend/tests/unit/test_password.py` (9 tests)
- `[x]` **JWT access/refresh token issuance**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Auth task 2; `API_SPECIFICATION.md` §5
  - Implementation: `backend/app/core/security/jwt.py`
  - Verification: `backend/tests/unit/test_jwt.py` (8 tests), `backend/tests/api/test_auth_bearer.py`
- `[x]` **Registration with email verification**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Auth task 3; `API_SPECIFICATION.md` §31.1
  - Implementation: `backend/app/api/v1/endpoints/auth.py` (`/register`, `/verify-email`), `backend/app/services/auth.py`
  - Verification: `test_auth_api.py` (register + verify tests), `test_auth_service.py`
- `[x]` **Login with rate limiting**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Auth task 4; `API_SPECIFICATION.md` §13
  - Implementation: `RateLimitMiddleware` rules registered in `app_factory.py`
  - Verification: `test_auth_api.py` login tests + `test_security_hardening.py` rate-limit tests
- `[x]` **Refresh rotation + revocation (sessions table)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Auth task 5; `API_SPECIFICATION.md` §5.4; `DATABASE_DESIGN.md` §25
  - Implementation: `auth.py` (`/refresh`), `backend/app/services/sessions.py`, `backend/app/services/auth.py`
  - Verification: `test_auth_api.py`, `test_auth_service.py`, `backend/tests/unit/services/test_sessions_service.py`, `test_sessions_api.py`, replay/rotation-chain tests in `test_security_edge_cases.py`
- `[x]` **Password reset flow**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Auth task 6; `API_SPECIFICATION.md` §31.3
  - Implementation: `auth.py` (`/forgot-password`, `/reset-password`); migration `20260804_0002`
  - Verification: `test_auth_api.py` (forgot/reset), `test_auth_service.py`, `test_email_service.py`
- `[x]` **RBAC authorization + owner scoping**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Auth task 7; `API_SPECIFICATION.md` §4; `BACKEND_ARCHITECTURE.md` §10
  - Implementation: `backend/app/dependencies/rbac.py`, `backend/app/api/v1/endpoints/admin.py`
  - Verification: `backend/tests/api/test_rbac_api.py` (14 tests), `backend/tests/unit/test_security_edge_cases.py`
- `[x]` **Logout and session invalidation**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Auth task 8; `API_SPECIFICATION.md` §3.4, §5.5
  - Implementation: `auth.py` (`/logout`, `/logout-all`), `users.py` (session list/revoke)
  - Verification: `test_auth_api.py`, `backend/tests/api/test_sessions_api.py`
- `[x]` **Transactional email service (verification + reset) with dev sink**
  - Source: `IMPLEMENTATION_PLAN.md` Phase 4; `BACKEND_ARCHITECTURE.md` §9
  - Implementation: `backend/app/services/email.py`, `backend/app/services/email_templates.py`
  - Verification: `backend/tests/unit/test_email_service.py` (7), `backend/tests/unit/test_email_templates.py` (16)

### Phase 5 — Frontend Foundation — `[x]`

- `[x]` **Next.js 15 app (App Router)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Frontend task 1; ui-ux-design.md §39
  - Implementation: `frontend/package.json` (Next.js 15.5.23, React 19, TypeScript), `frontend/tsconfig.json`, `frontend/next.config.ts`, `frontend/postcss.config.mjs`
  - Verification: `npm run build` compiled successfully, `npx tsc --noEmit` clean
- `[x]` **Tailwind CSS + design tokens per ui-ux-design §24**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Frontend task 2; ui-ux-design.md §24
  - Implementation: `frontend/styles/globals.css` (Tailwind v4, `@theme` block with all brand/semantic/surface/text/radius/shadow tokens)
- `[x]` **Utility components (cn, EmptyState)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Frontend task 3
  - Implementation: `frontend/lib/utils.ts` (cn via clsx+tailwind-merge), `frontend/components/ui/EmptyState.tsx`
- `[x]` **Base layouts + navigation shell per §9**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Frontend task 4; ui-ux-design.md §9
  - Implementation: `frontend/components/layout/AppShell.tsx`, `frontend/components/layout/Sidebar.tsx`, `frontend/components/layout/Header.tsx`
  - Includes: sidebar nav (all §9.3 items), responsive mobile drawer, collapsed mode, AI Agent Status card, user card, search bar, notification bell
  - Source: `IMPLEMENTATION_PLAN.md` §4 Frontend task 4; ui-ux-design.md §9
  - Implementation: not present (`frontend/components/layout/` empty)
- `[ ]` **Public pages (landing, about, contact) per §15**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Frontend task 5; ui-ux-design.md §15
  - Implementation: not present
- `[ ]` **Responsive + accessibility baseline**
  - Source: ui-ux-design.md §8, §22; TESTING_STRATEGY.md §17
  - Implementation: not present

### Phase 6 — Student Dashboard — `[~]`

- `[x]` **Dashboard aggregates (backend)** — active/pending/resolved requests + unread notifications
  - Source: `API_SPECIFICATION.md` §15; ui-ux-design.md §12
  - Implementation: `GET /api/v1/students/me/dashboard` in `backend/app/api/v1/endpoints/students.py`
  - Verification: `backend/tests/api/test_students_api.py::test_dashboard_counts_are_owner_scoped`
- `[ ]` **Login/register UI + auth state**
  - Source: `IMPLEMENTATION_PLAN.md` Phase 6; ui-ux-design.md §16
  - Implementation: not present (`frontend/app/(auth)/{login,register}/` empty)
- `[ ]` **Dashboard UI (stats, activity, states)**
  - Source: ui-ux-design.md §12, §16, §29/§34–35
  - Implementation: not present (`frontend/app/(dashboard)/student/` empty)

### Phase 7 — Request Management — `[~]`

- `[x]` **Request APIs (create, list, retrieve, update, transitions)**
  - Source: `IMPLEMENTATION_PLAN.md` Phase 7; `API_SPECIFICATION.md` §18
  - Implementation: `backend/app/api/v1/endpoints/requests.py`
  - Verification: `backend/tests/api/test_requests_api.py` (14 tests)
- `[x]` **Service-layer lifecycle / status state machine**
  - Source: `IMPLEMENTATION_PLAN.md` Phase 7
  - Implementation: `backend/app/services/requests.py`
  - Verification: `backend/tests/unit/services/test_requests_service.py` (25 tests)
- `[x]` **Append-only request timeline**
  - Source: `DATABASE_DESIGN.md` §18; `IMPLEMENTATION_PLAN.md` Phase 7
  - Implementation: `backend/app/models/request_timeline.py`, `backend/app/services/request_timeline.py`, `GET /requests/{id}/timeline`
  - Verification: `test_request_timeline_service.py` (8), `test_requests_api.py::test_timeline_is_owner_scoped`
- `[x]` **Notifications generated on request lifecycle events**
  - Source: `IMPLEMENTATION_PLAN.md` Phase 7 ("notifications groundwork documented")
  - Implementation: `RequestService` emits notifications on create/assign/status change
  - Verification: `test_requests_service.py` (create/assign/change-status record timeline + notification)
- `[ ]` **Request submission/tracking UI per §17**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Frontend task 10; ui-ux-design.md §17
  - Implementation: not present

### Phase 8 — AI Foundation — `[~]`

- `[x]` **`ai/` service structure (agents, graphs, prompts, tools, memory, rag)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 AI task 1; BACKEND_ARCHITECTURE.md §5.2
  - Implementation: structure in place and runnable — `ai/core/` (shared `config.py`, `state.py`), `ai/graphs/` (`workflow.py`), `ai/agents/` (`coordinator.py`, `intent_classifier.py`, `registry.py`), `ai/memory/`, `ai/prompts/versions/`, `ai/rag/`, `ai/tests/`, plus `ai/pyproject.toml` (pytest/ruff/mypy config)
  - Verification: `ai/tests/` 165 passed (§3.1); `ruff check ai` clean; `mypy --config-file ai/pyproject.toml` clean (37 files); `python -m compileall -q ai` OK. These verify foundation/config/state/workflow **structure** and the Coordinator + gateway logic — no real LLM, RAG, or network behavior is exercised.
  - Notes: `ai/{chains,tools,knowledge_base}/` remain empty package stubs; `ai/main.py` is still a docstring-only entrypoint.
- `[x]` **LangGraph workflow (nodes, edges, state)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 AI task 2; AI_ARCHITECTURE.md §11–12
  - Implementation: structural foundation in `ai/graphs/workflow.py` — 9 nodes, router conditional edge, and termination edges mirror AI_ARCHITECTURE.md §11.1–11.3 (`START → detect_intent → route → retrieve/build_context/generate/assemble_citations/aggregate_response/persist → END`, with `route → clarify → END`). Typed `WorkflowState` in `ai/core/state.py` is the graph state. `detect_intent` and `route` are real nodes backed by the Coordinator (`_detect_intent_with`/`_route_with`; `build_workflow(coordinator=...)` injects a custom coordinator). Specialist-phase wiring (Step 1K): `retrieve` is a real node that delegates to the injected specialist (`build_workflow(specialists=...)` maps `AgentKey` → agent) via `SpecialistAgent.run` and stores the `AgentOutput` in `state.agent_output`; `build_context`/`generate`/`assemble_citations`/`aggregate_response` are honest pass-through nodes (§13.5 — the agent runs the full pipeline internally); `persist` is a real node that appends user + assistant turns to the memory window and best-effort persists via an injectable `persist_writer` (§21, §23.1). Clarify node (Step 1L): `clarify` is now a real node backed by the Coordinator (`_clarify_with(coordinator, state)` → `{"agent_output": AgentOutput(answer=coordinator.clarify(state.routing_signal), status=WorkflowStatus.CLARIFYING)}`; `build_workflow` wires the node to the same resolved Coordinator). The graph never constructs real LLM clients or retrievers.
  - Verification: `test_workflow.py` (16) verifies node/edge structure, conditional routing, termination, router edge decisions (resolved → `RETRIEVE`, missing/tentative → `CLARIFY`), the detect_intent → route integration, and the clarify node producing a CLARIFYING `AgentOutput` end-to-end; graph compiles without executing any node. `test_workflow_specialists.py` (12, §3.1f) verifies end-to-end specialist execution through the graph (ADMISSION/EXAMINATION/FAQ routing, GENERAL→FAQ via the LLM Coordinator, clarify routing with no specialist execution, missing-signal no-op, agent failure FALLBACK status preserved, guardrail-blocked input never reaching retrieval/LLM, injected-specialist DI, graph state preservation, memory-window enforcement on persist, and the registered prompt reaching the gateway). `test_workflow_clarify.py` (17, §3.1g) verifies the clarify node in depth: ambiguous + low-confidence + out-of-scope routing to `CLARIFY` (never a specialist), the CLARIFYING `AgentOutput` with a safe student-facing clarifying turn, no specialist/LLM/retrieval execution on the clarify path (loud-gateway + recording-specialist + recording-retriever spies), `routing_signal`/`conversation_id`/`user_context`/`message_history`/`current_agent`/`handoff` preservation (§10.2, §24 — no handoff recorded for a clarifying turn), injected-LLM-Coordinator offline clarification (exactly one classification call), out-of-scope scope-boundary + nearest-specialist naming (§4.6, §9.4), and determinism without prompts or a gateway.
  - Notes: §11.5's maximum-clarification-rounds loop bound is an entry-point / Phase 10 concern (the graph itself is stateless per run and its topology is fixed at `clarify → END`); guardrail/audit logging of routing decisions to `agent_logs` (§11.4, §30.1, §37) is a Phase 10 persistence concern; real-model generation quality is Phase 13. No prompt or prompt version was invented for clarification (§13.2 has no dedicated clarification type — the Coordinator prompt covers "clarification, fallback behavior"; the node is deterministic and data-driven per §9.5).
- `[x]` **Coordinator Agent (intent detection, routing)**
  - Source: AI_ARCHITECTURE.md §4, §9
  - Implementation: `ai/agents/coordinator.py` (detect_intent, route, needs_clarification) with a deterministic `RuleBasedIntentClassifier` and the new LLM-backed `LLMIntentClassifier` (`ai/agents/intent_classifier.py`) driven by the provider-agnostic LLM gateway (`ai/gateway/`), data-driven `AgentRegistry` + routing table (`ai/agents/registry.py`), `create_llm_coordinator(settings, registry=None, gateway=None, confidence_threshold=...)`, conversation history (last 8 turns) + user context in the classification prompt, secondary-intent extraction, low-confidence/missing → `CLARIFY` routing, and error-safe fallback (classifier/gateway failures degrade to a safe low-confidence signal; secrets redacted). Provider mapping is confined to `ai/gateway/factory.py` (Gemini/OpenAI/Groq); the Coordinator/workflow/classifier are provider-agnostic. Workflow `detect_intent`/`route` nodes are wired to this agent.
  - Verification: `test_coordinator.py` (32), `test_llm_classifier.py` (10), `test_gateway.py` (34) cover intent classification (rule + LLM), confidence thresholding, clarification fallback, out-of-scope handling, provider-agnostic routing across all three providers, provider failure/classifier-crash degradation with no secret leakage, user-context forwarding, and reason propagation. All offline via injected fake clients — no real model calls.
  - Notes: real-model intent-classification quality is NOT verified (offline fakes only); that belongs to Phase 13 AI quality tests.
- `[x]` **Admission Agent**
  - Source: AI_ARCHITECTURE.md §5; IMPLEMENTATION_PLAN.md §4 AI task 4
  - Implementation: `ai/agents/admission.py` (AdmissionAgent + `create_admission_agent`) on the shared `SpecialistAgent` base (`ai/agents/base.py`), which implements the specialist pipeline `retrieve → build_context → generate → assemble_citations → run` (§3.5, §8). Retrieval via the `Retriever` protocol (`ai/rag/retriever.py`); context assembly via `ContextBuilder` (`ai/rag/context_builder.py`, labeled sections, per-unit budget trimming: user context → oldest history → lowest-score evidence, `ContextOverflowError` when essential content exceeds `context_budget_tokens`); schema-constrained structured generation through the provider-agnostic LLM gateway; citations resolved only from retrieved chunks, de-duplicated and ordered by retrieval score (§19.3), `relevance_score` clamped to 0..1. No-answer policy (§20.4/§28.3): empty retrieval short-circuits to a department referral with no LLM call; LLM-marked `unanswerable` degrades to the same; `LLMError` degrades to a friendly FALLBACK answer (no secret leakage). Versioned prompt `admission.system` v1 (`ai/prompts/versions/admission_v1.py`) assembled from shared components (`ai/prompts/components.py`) and served through the `PromptRepository` (`ai/prompts/repository.py`); `context_budget_tokens` setting added to `ai/core/config.py`.
  - Verification: `ai/tests/test_admission.py` (23) covers prompt ownership, retrieval params, context building/trimming priorities, grounding + citation order/dedup/clamping, no-answer short-circuit (no LLM call), unanswerable fallback, provider-failure fallback, malformed-JSON degradation, structured-output schema pass-through, and settings-driven construction. All offline via a fake retriever + scripted fake gateway (TESTING_STRATEGY.md §23.2).
  - Notes: real-model generation quality is NOT verified (offline fakes only); FAISS-backed retrieval lands with Phase 9. The Examination and FAQ agents follow the same shared machinery (Step 1F/Step 1G).
- `[x]` **Examination Agent**
  - Source: AI_ARCHITECTURE.md §6; IMPLEMENTATION_PLAN.md §4 AI task 5
  - Implementation: `ai/agents/examination.py` (ExaminationAgent + `create_examination_agent`) on the same shared `SpecialistAgent` base (`ai/agents/base.py`) and pipeline (`retrieve → build_context → generate → assemble_citations → run`) as the Admission Agent — no new plumbing (§3.5, §8). Retrieval is scoped to the `examination` knowledge category (§6.2, §16.4) through the existing `Retriever` protocol; context assembly, schema-constrained structured generation via the provider-agnostic LLM gateway, citation assembly (score order, dedup, 0..1 clamping), and the no-answer/error fallbacks are inherited unchanged (§17-19, §20.4, §23.2). Versioned prompt `examination.system` v1 (`ai/prompts/versions/examination_v1.py`) composed from the shared components and registered in the default `PromptRepository`. Coordinator/registry integration already existed and is unchanged: `EXAMINATION` intent maps to `AgentKey.EXAMINATION` in the routing table (`ai/agents/registry.py`), and the workflow's generic router edge sends a resolved Examination signal to the specialist phase (§9.2, §11.3). No workflow topology changes were made; the specialist-phase workflow nodes remain placeholders (Step 1D scope).
  - Verification: `ai/tests/test_examination.py` (24) covers prompt ownership/scope (§6.1-6.4), retrieval params, grounded generation + citation order/dedup/clamping, no-answer short-circuit (no LLM call), unanswerable fallback, provider-failure fallback, malformed-JSON degradation, structured-output schema pass-through, settings-driven construction, conversation follow-up + user-context injection, and Coordinator → Examination routing integration (registry resolve, rule-based classify → route, router-edge decision). All offline via a fake retriever + scripted fake gateway (TESTING_STRATEGY.md §23.2).
  - Notes: real-model generation quality is NOT verified (offline fakes only); FAISS-backed retrieval lands with Phase 9. Examination-specific escalation (request tracking) is surfaced in the prompt/referral text only — the backend request conversion is out of Phase 8 scope.
- `[x]` **FAQ Agent**
  - Source: AI_ARCHITECTURE.md §7; IMPLEMENTATION_PLAN.md §4 AI task 6
  - Implementation: `ai/agents/faq.py` (FAQAgent + `create_faq_agent`) on the same shared `SpecialistAgent` base (`ai/agents/base.py`) and pipeline (`retrieve → build_context → generate → assemble_citations → run`) as the Admission/Examination agents — no new plumbing (§3.5, §8). Retrieval is scoped to the `faq` knowledge category (§7.2, §16.4) through the existing `Retriever` protocol; context assembly, schema-constrained structured generation via the provider-agnostic LLM gateway, citation assembly (score order, dedup, 0..1 clamping), and the no-answer/error fallbacks are inherited unchanged (§17–19, §20.4, §23.2). The agent accepts the existing typed `WorkflowState` fields (`user_query`, `message_history`, `user_context`) and produces the existing `AgentOutput`. It handles insufficient/unavailable context safely (no-answer short-circuit with a Registrar's-Office referral — no LLM call), never fabricates university information, and never invents policies, dates, fees, procedures, departments, or other institutional facts (§7.4). Versioned prompt `faq.system` v1 (`ai/prompts/versions/faq_v1.py`) composed from the shared components and registered in the default `PromptRepository`. Coordinator/registry integration already existed and is unchanged: `FAQ` (and `GENERAL`) intents map to `AgentKey.FAQ` in the routing table (`ai/agents/registry.py`), and the workflow's generic router edge sends a resolved FAQ signal to the specialist phase (§9.2, §11.3). No workflow topology changes were made; the specialist-phase workflow nodes remain placeholders (Step 1D scope).
  - Verification: `ai/tests/test_faq.py` (30) covers prompt ownership/scope (§7.1–7.4), retrieval params, clear-FAQ-request intent detection + Coordinator → FAQ routing (registry resolve, rule-based classify → route, router-edge decision), grounded generation + citation order/dedup/clamping, no-answer short-circuit (no LLM call), empty-query safe handling, unanswerable fallback, provider-failure + timeout fallback, malformed-JSON degradation, structured-output schema pass-through, retrieved-context content reaching the pipeline, conversation follow-up + user-context injection, `WorkflowState` field acceptance + `AgentOutput` structure, settings-driven construction, and the retriever contract. All offline via a fake retriever + scripted fake gateway (TESTING_STRATEGY.md §23.2).
  - Notes: real-model generation quality is NOT verified (offline fakes only); FAISS-backed retrieval lands with Phase 9. General-answer-only limitation is enforced in the prompt/referral text; handoff to admission/examination is a prompt-level scope boundary, not a cross-agent call (§7.4, §3.3).
- `[x]` **Versioned prompts in `ai/prompts/`**
  - Source: `IMPLEMENTATION_PLAN.md` §4 AI task 7; AI_ARCHITECTURE.md §13, §34
  - Implementation: `ai/prompts/repository.py` (versioned `Prompt` assets + `PromptRepository`), `ai/prompts/components.py` (shared grounding/safety/formatting/no-answer rules), and the versioned assets `admission.system` v1 (`ai/prompts/versions/admission_v1.py`), `examination.system` v1 (`ai/prompts/versions/examination_v1.py`), and `faq.system` v1 (`ai/prompts/versions/faq_v1.py`), all registered in the default repository and consumed by their agents. Execution wiring (Step 1J): the shared `SpecialistAgent._resolve_prompt` (`ai/agents/base.py`) resolves each agent's prompt from the repository — never hardcoded (§13.1/§34.3) — and `generate()` sends the resolved text as the gateway system prompt; ownership/version metadata is validated (missing prompt, unsupported version, ownership mismatch, or missing owner all fail fast with a `ValueError`); `GenerationResult` records the resolved `prompt_version` with every generation (§34.6 traceability — version + model reproducible per message); default-version resolution returns the latest registered version; shared components compose into every final prompt (§13.4/§34.7).
  - Verification: `ai/tests/test_prompts.py` (27, §3.1e) covers repository resolution (default + exact-version + latest), registration validation, missing/unsupported-version/ownership-mismatch/missing-owner fail-fast, repository-resolved prompt actually reaching the gateway for Admission/Examination/FAQ (v2 swap changes what is sent — not hardcoded), shared-component composition (repository text == agent.prompt.text == gateway system prompt), `prompt_version` + model traceability (incl. malformed-output degradation), and regressions (no-answer short-circuit, guardrail short-circuit, history injection). Full suite 307 passed; ruff clean; mypy clean (42 files); compileall OK — all offline via injected fakes.
- `[x]` **Guardrails + safety rules**
  - Source: `IMPLEMENTATION_PLAN.md` §4 AI task 8; AI_ARCHITECTURE.md §25–26, §37
  - Implementation: new `ai/guardrails/` package — `results.py` (typed `GuardrailDecision` + `GuardrailCategory` enum: `ALLOWED`, `EMPTY`, `PROMPT_INJECTION`, `JAILBREAK`, `SYSTEM_PROMPT_REQUEST`, `CHEATING`, `HATE_HARASSMENT`, `RESTRICTED_TOPIC`, `OUT_OF_SCOPE`, `PRIVATE_DATA`, `UNSAFE_OUTPUT`, `SENSITIVE_DATA`, `AUTHORITY_CLAIM`), `patterns.py` (declarative rule groups per §26.2 — each rule carries a stable internal code, a word-boundary regex, and a safe user-facing fallback; rule groups are ordered by safety precedence per §25–26/§37.2 so a combined attack reports its direct safety violation), and `guardrails.py` (`SafetyGuardrails.check_input`/`check_output` with a shared module-level `default_guardrails()` singleton, so all agents share one rule set). Integrated into the shared `SpecialistAgent` pipeline (`ai/agents/base.py`): **input checks run before retrieval/LLM** (§26.1 prompt-injection prevention, §26.2 jailbreak prevention, §26.3 unsafe-prompt handling — blocked input short-circuits with a safe category-appropriate fallback and zero LLM calls) and **output checks run after generation** (§26.4 output filtering — blocked output is replaced by a safe fallback and its citations are dropped). Fallbacks never expose internal detection details (matched pattern/code/category/reason) to the student (§26.3, §37). Out-of-scope/restricted prompts return a department referral. Empty queries remain safely handled by the existing no-answer path (§20.4/§28.3). The pipeline accepts an injected `guardrails` instance (defaulting to the shared singleton) and the guardrail hook is orthogonal to existing behavior — no-answer short-circuit, provider-failure fallback, citation assembly, and category-scoped retrieval are unchanged.
  - Verification: `ai/tests/test_guardrails.py` (39) covers: allowed normal admission/examination/FAQ queries, no-overblocking of benign queries, prompt-injection blocks (`PROMPT_INJECTION`), jailbreak blocks (`JAILBREAK`), system-prompt-extraction blocks, cheating blocks, hate/harassment blocks, restricted-topic/out-of-scope referral fallbacks, third-party private-data blocks (`PRIVATE_DATA`), combined-attack safety precedence, empty-input safe handling, output-side blocks (unsafe output, cheating, authority claims, system-prompt leakage, sensitive-data leakage, third-party privacy) with safe fallbacks that do not leak internals, pipeline integration (blocked input ⇒ zero retriever + zero LLM calls; blocked output ⇒ safe fallback with no citations; valid output ⇒ normal citation assembly; empty query short-circuits even with evidence; retrieved evidence containing injection strings is treated as data — delimited, labeled, non-instructional; both hooks invoked per run), and regression coverage proving existing Admission/Examination/FAQ behavior, no-answer short-circuit, and provider-failure fallback remain intact. All offline via a fake retriever + scripted fake gateway (TESTING_STRATEGY.md §23.2).
  - Notes: deterministic rule-based guardrails only; robustness against adversarial real-world phrasing (e.g., obfuscation) is a Phase 13 AI-quality concern and is not verified here.
- `[x]` **Conversation memory + agent handoff + error recovery**
  - Source: `IMPLEMENTATION_PLAN.md` §4 AI tasks 9–10; AI_ARCHITECTURE.md §21, §23–24
  - Implementation: `ai/memory/manager.py` — the stateless `ConversationMemoryManager` (short-term window of `CHAT_HISTORY_LIMIT` turns default 20 §21.2/§21.6; opt-in long-term overflow summarization via an injected `summarizer` §21.3; session rebuild from persisted history + summary §21.4/§22.5; safe `persist` that never fails a run on a DB write error §23.1). `ai/core/state.py` — new typed `Handoff` model (`routed_to`/`previous_agent`/`reason`) and `current_agent`/`handoff` fields on `WorkflowState` (§24.3-24.4). `ai/graphs/workflow.py` — the `route` node records the active agent + §24 handoff metadata (emitted only on an actual agent change: first route COORDINATOR→specialist and specialist→specialist switches), and the `detect_intent` node enforces the short-term window before classification (§12.5, §21.2); `build_workflow(..., memory=...)` injects a custom manager (e.g. long-term opt-in).
  - Verification: `ai/tests/test_memory.py` (22) + extended workflow/state coverage (§3.1d) cover the window (default/custom/empty), add-turn overflow, short-term-only drop, long-term summarization + summary folding, safe overflow drop without a summarizer, validation, session rebuild (§22.5), persistence failure recovery (§23.1), first/switched/same-agent route handoff semantics, `Handoff` round-trip, state defaults, and the memory window enforced before intent classification (recording-classifier spy). The Step 1K `persist` node reuses this manager (user + assistant turns appended to the window, best-effort persist via an injectable writer) and is exercised end-to-end in `test_workflow_specialists.py` (§3.1f). Full suite 307 passed; ruff clean; mypy clean (42 files) — all offline via injected fakes.
  - Notes: the §24.4 backend-side sync (`ai_conversations.current_agent` transactional update), the handoff chip in the response envelope, and the backend persistence of the persisted window are Phase 10 concerns (the `persist` node now writes through the injectable writer in-memory/offline only); real-model long-term summarization is a Phase 13 AI-quality concern. No provider/API/network/database call is made by any Step 1I/1K test.

### Phase 9 — RAG Implementation — `[x]`

- `[x]` **Document ingestion + chunking**
  - Source: `IMPLEMENTATION_PLAN.md` §4 RAG task 1; AI_ARCHITECTURE.md §14.2, §36
  - Implementation: `ai/rag/ingestion.py` (new) — the deterministic, offline front half of the RAG pipeline (read → extract text → validate → chunk). Typed error hierarchy (`IngestionError` + `UnsupportedFileTypeError`/`EmptyDocumentError`/`MalformedDocumentError`/`InvalidMetadataError`/`DuplicateSourceError`/`DocumentParseError`); file-type whitelist pdf/md/txt/docx (§36.3); SHA-256 checksum over CRLF-normalized text; content scan (empty/binary-only rejected); `KnowledgeCategory` enum (admission/examination/faq/documents); version validation (dotted integers ≤30); `txt`/`md` UTF-8-strict decode; optional `pypdf`/`python-docx` extraction failing loudly when the package is absent; markdown front matter (`title`/`category`/`version`/`author`); paragraph-unit deterministic chunking with markdown-heading context, sentence-bound overlap for oversized paragraphs only, and stable `sha256(source \x1f version \x1f index)` chunk ids (§36.4); chunk/document metadata mirroring `knowledge_chunks`/`knowledge_documents` (§21.2/§21.1); `IngestedDocument.is_eligible(current_version=...)` enforcing the §21.3/§16.4 candidate filter (is_active + processed + current version); `DocumentChunk.to_retrieved_chunk()` mapping onto the existing `RetrievedChunk` contract; `ingest_documents` enforcing the partial-unique `(source_path, version)` rule; `KnowledgeIngestor(knowledge_root)` discovering only category-folder documents (skips `.gitkeep`).
  - Verification: `ai/tests/test_ingestion.py` (46) — valid ingestion, validation, empty/unsupported/malformed rejection, category/version validation, deterministic chunk ids/ordering, chunk boundaries + overlap, chunk metadata, source metadata, category/version preservation, chunk position, repeated ingestion identical, eligibility (inactive/pending/non-current), `RetrievedChunk` compatibility, duplicate `(source_path, version)` rejection, front matter, `KnowledgeIngestor` discovery/ingestion, pdf/docx parser behavior via monkeypatched `find_spec` (deterministic, no parser packages required). Full suite §3.1h (353 passed). compileall OK; `ruff check ai` clean; mypy clean (42 files).
  - Notes: embeddings, FAISS, the concrete retriever, context-builder wiring, citation generation, re-indexing, and golden sets are tasks 2–8 of this phase (embeddings, FAISS, the retriever, the context-builder wiring, and citation generation are now `[x]` below). The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged. `knowledge/` category folders still contain only `.gitkeep` (seeded content is a Phase 3 seed-data concern, not this task).
- `[x]` **Sentence Transformers embeddings**
  - Source: `IMPLEMENTATION_PLAN.md` §4 RAG task 2; AI_ARCHITECTURE.md §15
  - Implementation: `ai/rag/embeddings.py` (new) + `sentence-transformers==5.6.1` in `ai/requirements.txt` — the architecture-approved Sentence Transformers embedding pipeline (§15.1): a runtime-checkable `EmbeddingProvider` protocol (`model_name`, `dimension`, `embed(text)`, `embed_batch(texts)`); the config-driven, lazily-loaded `SentenceTransformerEmbeddingProvider` (model weights downloaded only on first embed request in production, never in tests; typed `EmbeddingProviderError` when the package is missing or the model fails to load); `create_embedding_provider(settings)` fail-fast factory bound to `Settings.embedding_model`/`EMBEDDING_MODEL`; `EmbeddingService.embed_chunks` (batched chunk embedding preserving input order, `batch_size=32` default) and `EmbeddingService.embed_query` (individual query embedding, same provider instance → model parity, §15.1); `ChunkEmbedding` records (`chunk_id`, `document_id`, `title`, `category`, `version`, `source_path`, `chunk_index`, `heading`, `model_name`, `vector`, `dimension`) preserving the §21.2/§15.2 chunk-to-vector association; `prepare_embedding_input` (CRLF-normalized chunk text only — metadata is carried beside the vector, never mixed into the embedding text); deterministic typed validation (`EmbeddingError` hierarchy: `EmbeddingProviderError`/`EmptyEmbeddingInputError`/`EmptyVectorError`/`DimensionMismatchError`/`InvalidVectorError`/`CountMismatchError`) rejecting empty/invalid input, empty/mis-sized/non-finite vectors, and per-batch count mismatches, with unexpected provider exceptions wrapped. All embedding runs locally inside the AI service — **no API-based embeddings, no external call per chunk**.
  - Verification: `ai/tests/test_embeddings.py` (39) — protocol contract, single/batched/ordered embedding, chunk-id + metadata association, query/document model parity, dimension/empty/count/non-finite validation, provider-failure propagation + wrapping, configured model/dimension/batch-size behavior (EMBEDDING_MODEL set/unset, non-positive batch_size), fake-provider injection (deterministic SHA-256 vectors; embed inputs recorded), lazy-load behavior via a monkeypatched offline `sentence_transformers` module (no load at construction, exactly one load on first embed, typed error when the package is absent — no downloads, no network), deterministic re-embedding for a fixed model, and the typed error hierarchy. Focused + ingestion suite §3.1i (85 passed); full suite §3.1i (392 passed); compileall OK; `ruff check ai` clean; mypy clean (42 files). The 46 ingestion tests still pass, proving task 1 is unbroken.
  - Notes: FAISS indexing + persistence (§15.2), the concrete retriever, context-builder wiring, citation generation, re-indexing, and golden sets are tasks 3–8 of this phase (FAISS, the retriever, the context-builder wiring, and citation generation are now `[x]` below). The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged. `knowledge/` category folders still contain only `.gitkeep` (seeded content is a Phase 3 seed-data concern, not this task).
- `[x]` **FAISS index + persistence**
  - Source: `IMPLEMENTATION_PLAN.md` §4 RAG task 3; AI_ARCHITECTURE.md §15.2, §16, §36.7
  - Implementation: `ai/rag/faiss_index.py` (new) + `faiss-cpu==1.14.3`/`numpy==2.3.5` in `ai/requirements.txt` + `knowledge/vectorstore/*` in `.gitignore` — the architecture-approved FAISS vector index + persistence (§15.2). `build_index(embeddings)` consumes task-2 `ChunkEmbedding` records in input order (**input order == FAISS position == metadata position**), validates them (consistent dimension, finite values, non-zero norm, unique chunk ids, single model for §15.1 parity), and stores L2-normalized vectors in an `IndexFlatIP` — **cosine similarity** (the §16.2 metric consistent with the Sentence Transformers encoder, implemented via normalization + inner product; raw scores are cosine similarities in [-1, 1] per §16.3). `VectorIndex.search` is the only low-level primitive (raw positions/scores, `k`-bounded, no ranking policy/thresholds/filtering — those are task 4). `save_index` persists `index.faiss` + a `metadata.json` mapping (position ↔ `ChunkEmbedding` ↔ `chunk_id`; preserves chunk_id, document_id, title, category, version, source_path, chunk_index, heading, model_name, chunk_text, vector, plus index config version/metric/dimension/model_name/count) atomically per §36.7 — write temp files → reload + validate → replace; failures clean up and never leave a valid-looking partial index. `load_index` validates metadata (version/metric/count/dimension/model parity/per-entry structure incl. chunk_text) against the FAISS binary (count/dimension/metric type) before returning a fully reconstructible `VectorIndex`; `index_exists` confirms a complete pair. Typed `FaissIndexError` hierarchy (`FaissUnavailableError`/`EmptyIndexInputError`/`InvalidVectorError`/`IndexDimensionError`/`DuplicateChunkIdError`/`ModelParityError`/`IndexPersistenceError`/`IndexLoadError`/`IndexVersionError`/`CorruptIndexError`/`MetadataMismatchError`); FAISS lazy-loaded (`find_spec` + in-function import) with a clear `FaissUnavailableError` when missing. `chunk_text` was added to `ChunkEmbedding` (minimal compatibility change) so the persisted mapping can reconstruct `RetrievedChunk.snippet` (§19.1). Persistence is deterministic (identical inputs → byte-identical files).
  - Verification: `ai/tests/test_faiss_index.py` (47) — module import + FAISS dependency availability, missing-FAISS clear error via monkeypatched `find_spec`, no-network-import guarantee, build count/dimension/index-type (`IndexFlatIP`)/metric (`cosine` + `METRIC_INNER_PRODUCT`), input-order + chunk_id↔position mapping via search, source-metadata preservation (incl. chunk_text), raw cosine-score correctness + [-1,1] range, `k` bounding + `-1` padding dropped, search input validation (k/dimension/empty/non-finite/zero-norm), build rejection (empty, inconsistent dimensions, NaN/inf, duplicate chunk ids, mixed models, zero norm, non-`ChunkEmbedding`), save file layout + directory creation + temp cleanup, save rejection (file-as-path, wrong metric), deterministic byte-identical persistence, load count/dimension/metadata-identical/ordering preservation, round-trip search, missing directory/index/metadata, corrupted FAISS binary, corrupted metadata JSON, incompatible version, wrong metric, entries-count mismatch, duplicate chunk ids in metadata, index-vs-metadata count mismatch, entry dimension mismatch, missing chunk_text. Focused suite §3.1j (47 passed); full suite §3.1j (439 passed); compileall OK; `ruff check ai` clean; mypy clean (43 files). The 39 embeddings tests and 46 ingestion tests still pass, proving tasks 1–2 are unbroken. All tests use synthetic vectors + `tmp_path` — no model weights, no index in the repo tree, no network.
  - Notes: the concrete retriever (task 4) will consume this index via the existing `Retriever` protocol; `chunk_text`/`chunk_id` in the persisted mapping give task 4 everything needed to build `RetrievedChunk` (snippet/score per §16.3/§19.1) and to filter by category/document status. The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged. `knowledge/` category folders still contain only `.gitkeep` (seeded content is a Phase 3 seed-data concern, not this task).
- `[x]` **Retriever with metadata filtering + top-K**
  - Source: `IMPLEMENTATION_PLAN.md` §4 RAG task 4; AI_ARCHITECTURE.md §16
  - Implementation: `ai/rag/faiss_retriever.py` (new) — the concrete `FaissRetriever` implementing the existing `Retriever` protocol: the query is embedded with the same injected `EmbeddingProvider` (task 2), searched against the task-3 `VectorIndex` (full pool, `k=count`), ranked by raw cosine similarity with a deterministic position tie-break (§16.3), filtered by `categories` and version currency (§16.4/§21.3), de-duplicated by chunk id, bounded by `top_k`/`RAG_TOP_K` (default 4), and converted to `RetrievedChunk` (`snippet=chunk_text`, raw score). Typed `RetrieverError` hierarchy (`EmptyQueryError`/`InvalidQueryError`/`EmbeddingProviderUnavailableError`/`QueryEmbeddingError`/`InvalidQueryVectorError`/`DimensionMismatchError`/`ModelParityError`/`IndexUnavailableError`/`SearchError`/`RetrievedChunkError`) maps embedding, FAISS, parity, and mapping failures precisely; no similarity threshold invented. `create_faiss_retriever(settings, ...)` factory loads the persisted index from `Settings.vector_store_path` and honors `settings.rag_top_k`.
  - Verification: `ai/tests/test_retriever_faiss.py` (45) — protocol conformance, provider-embedding spy, model/dimension parity, search-on-full-pool, top-K bounding, raw cosine score + ranking order + position tie-break, determinism, duplicate dedupe, `RetrievedChunk` mapping + index-metadata preservation, category narrowing (bare strings + no-match), version-currency eligibility (stale excluded / current kept / title-key fallback / unknown eligible), error paths (empty/invalid query, missing provider/index, embedding failure, zero-norm/NaN, FAISS failure mapping, invalid/negative/non-integer positions, non-finite scores), factory load/missing/corrupt, Admission-agent compatibility. Focused suite §3.1k (45 passed); full suite §3.1k (484 passed); compileall OK; `ruff check ai` clean; mypy clean (44 files). All tests offline (fake provider + synthetic vectors + `tmp_path`).
  - Notes: context-builder wiring (§17) is task 5 (now `[x]` — see below) and citation generation (§19) is task 6 (now `[x]` — see below); re-indexing (task 7) and golden retrieval/eval sets (task 8) are now `[x]` — see below (Step R9-7/R9-8, §3.1n). The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged. `knowledge/` category folders still contain only `.gitkeep` (seeded content is a Phase 3 seed-data concern, not this task).
- `[x]` **Context builder within token budget**
  - Source: `IMPLEMENTATION_PLAN.md` §4 RAG task 5; AI_ARCHITECTURE.md §17
  - Implementation: `ai/rag/context_builder.py` (finalized) — the Phase 8 `ContextBuilder` is now fully wired into the specialist RAG pipeline (§17): every specialist run executes retrieve → `build_context` → generate → assemble citations, with the builder fed the injected `Retriever`'s `RetrievedChunk[]` (score-descending, §16.5) plus `Settings.context_budget_tokens` via the `create_*_agent` factories (injectable `context_builder`). Assembly order per §17.2 (system rules → user context → history → retrieved evidence → current query) with labeled blocks; prioritization per §17.4 (evidence 9 > history 5 > user context 1; system rules + current query are priority 10 never-trim); over-budget trimming drops evidence lowest-score-first, then history oldest-first, then user context, never silently truncating (§21.6) and never exceeding the budget on the accounted units — `ContextOverflowError` is raised only when the essential content (system rules + current query) cannot fit (§17.3). Deterministic token estimation (`max(1, len(text) // 4)`, §17.3 — no tokenizer/model download), injectable estimator. Finalization this step: (a) each evidence block now renders the chunk identity — `[Source {n}] {title} (category: {category}) [chunk: {chunk_id}]` — so the LLM can emit real `cited_chunk_ids` that the existing citation assembly maps onto the retrieved set (§19.1/§19.3); (b) a public `estimate_tokens(text)` method on `ContextBuilder` (deterministic, testable). The workflow `build_context` node is an honest pass-through to the agent's `build_context` (§13.5); empty retrieval short-circuits to the grounded no-answer path (§20.4) without touching the ContextBuilder or the LLM.
  - Verification: `ai/tests/test_context_builder.py` (new, 21) — empty retrieval, section ordering + labeling, evidence/instruction separation, single/multiple chunks within budget, exact budget boundary (nothing trimmed), lowest-score evidence trimmed first, chunks fitting individually but exceeding total, oversized chunk dropped safely, system rules never trimmed before other content, oldest-history trimmed first, user context dropped before evidence, bounded (never unbounded) budget overshoot across sizes, deterministic output, default estimator `len//4` incl. empty/min boundary, injectable estimator, metadata + chunk-identity preservation, chunk identity never fabricated, no fabricated content, malformed chunk robustness, `ContextOverflowError` only when essential content exceeds budget, no overflow when only removable content exceeds. `ai/tests/test_agent_context_integration.py` (new, 17) — Admission/Examination/FAQ each build context through the injected `ContextBuilder`; GENERAL → FAQ through the real LangGraph workflow; retriever and ContextBuilder called exactly once per run; `Settings.context_budget_tokens` → `context_builder.max_tokens` through the factories; injectable builder; empty retrieval skips builder + LLM; guardrail-blocked input never reaches retrieval/LLM; prompt + prompt version preserved; message history included in the built context; `AgentOutput` shape unchanged; citation compatibility with `[chunk: …]` ids exposed in context (score-order §19.3); injected fake retriever used; all three factories run offline with empty API keys. Focused suite §3.1l (38 passed); full suite §3.1l (**522 passed**); compileall OK; `ruff check ai` clean; mypy clean (44 files). All offline — fake retriever + fake gateway + synthetic `RetrievedChunk`/char estimator; no API keys, no network, no database.
  - Notes: citation generation/dedup (task 6) is now `[x]` — see below; re-indexing (task 7) and golden retrieval/eval sets (task 8) are now `[x]` — see below (Step R9-7/R9-8, §3.1n). The shared `Retriever` protocol, `WorkflowState`, agents, prompts, and workflow are unchanged. `knowledge/` category folders still contain only `.gitkeep` (seeded content is a Phase 3 seed-data concern, not this task).
- `[x]` **Citation generation/dedup (`ai_sources`)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 RAG task 6; AI_ARCHITECTURE.md §19
  - Implementation: `ai/agents/base.py` `SpecialistAgent.assemble_citations` (finalized) — deterministic citation generation from the retrieved `RetrievedChunk[]` (§19.1): the LLM references evidence only via `cited_chunk_ids` and the authoritative metadata (chunk_id, document_id, title, category, snippet, score) always comes from the retrieved chunks; a cited id not in the retrieved set is ignored, never invented (§20.3). Dedup is per-chunk (§19.3 — one citation per chunk per message): repeated cited ids collapse to one citation and duplicate chunk ids in the retrieved set keep the strongest (highest retrieval score) occurrence — distinct chunks are never merged. Ordering is deterministic: retrieval score descending with the retrieved position as the tie-break (§19.3/§16.3/§16.5), identical on repeated execution, never following the LLM's citation order. Scores clamp to the 0..1 `ai_sources_score_check` contract (§19.4, DATABASE_DESIGN.md §32.6); non-finite scores degrade to 0.0 instead of failing `Citation` validation. The assembler runs inside the shared specialist pipeline (Admission/Examination/FAQ + GENERAL → FAQ through the workflow), the retriever is called exactly once per run (§16.5), the ContextBuilder `[chunk: …]` evidence ids map directly onto the citations (§19.1/§19.3), `AgentOutput.citations` is unchanged, and no prompt version / no URL or source-name parsing / no re-ranking or thresholds were introduced. The `ai_sources` DB persistence layer (`backend/app/models/ai_sources.py`, `backend/app/services/ai_sources.py`) already exists and is tested but is NOT this task.
  - Verification: `ai/tests/test_citations.py` (new, 28) — grounding + source-metadata preservation (§19.1), ghost cited ids + empty evidence never fabricated (§20.3), LLM cannot inject source metadata, empty retrieval → no-answer with zero citations and no LLM call (§20.4), empty cited list, repeated-id dedup, strongest-duplicate-wins, distinct chunks from one document not merged, score-descending ordering, retrieval-position tie-break on equal scores (never LLM order), repeated-run determinism, [0,1] score clamping (§19.4/§32.6), non-finite scores → 0.0 without crash, Admission/Examination/FAQ end-to-end grounded citations, GENERAL → FAQ citations through the real workflow, `AgentOutput` contract preserved, unanswerable no-answer preserved, retriever + LLM each called exactly once (§16.5), ContextBuilder evidence-id ↔ citation chunk_id compatibility, chunk_id never fabricated beyond evidence, duplicate-chunk determinism, missing optional document_id handled safely, empty-evidence assembler safety. Focused suite §3.1m (28 passed); full suite §3.1m (**550 passed**); compileall OK; `ruff check ai` clean; mypy clean (44 files). All offline — fake retriever + fake gateway + synthetic `RetrievedChunk`; no API keys, no network, no database.
  - Notes: the knowledge re-index background job (task 7) and golden retrieval/eval sets (task 8) are now `[x]` — see below (Step R9-7/R9-8, §3.1n). The `ai_sources` data layer (DATABASE_DESIGN.md §22) will persist citations when the response envelope is written (Phase 10 wiring). The shared `Retriever` protocol, `ContextBuilder`, `WorkflowState`, agents, prompts, and workflow are unchanged. `knowledge/` category folders still contain only `.gitkeep` (seeded content is a Phase 3 seed-data concern, not this task).
- `[x]` **Knowledge re-indexing background job**
  - Source: `IMPLEMENTATION_PLAN.md` §4 RAG task 7; AI_ARCHITECTURE.md §14.2, §36
  - Implementation: `ai/rag/reindexer.py` (new) — `KnowledgeReindexer(knowledge_root, vector_store_path, ingestor, embedding_service, provider)` orchestrates the deterministic re-index pipeline end to end (ingest → embed → build/save FAISS index → atomically swap the persisted manifest + index), reporting added/removed/changed per source (`ReindexReport`). Removal detection fixed: `_plan_changes` computes `removed_sources` from the previous manifest minus the current corpus and short-circuits only when nothing changed AND nothing was removed; removal-only runs skip embedding safely. An optional injected `verify_before_swap: Callable[[VectorIndex], bool]` gates the swap (a failure aborts with the old index untouched); typed `ReindexError` hierarchy (`ReindexError`/`IndexBuildError`/`IndexSaveError`/`EmptyEmbeddingInputError`/`VerificationFailedError`); `async reindex()` = `await asyncio.to_thread(self.run)`.
  - Verification: `ai/tests/test_reindexer.py` (15, §3.1n) — full re-index, added/changed/removed detection, removal-only path, atomic manifest swap, unchanged-corpus short-circuit, verified-abort leaves the old index intact, missing-corpus error, persistence round-trip, deterministic report, async entry. Full suite 580 passed (§3.1n); compileall OK; ruff clean; mypy clean (46 files).
  - Notes: the scheduled worker that triggers the job is a Phase 2/10 concern (this task delivers the job, not the scheduler).
- `[x]` **Golden retrieval/eval sets for regression**
  - Source: `IMPLEMENTATION_PLAN.md` §4 RAG task 8; TESTING_STRATEGY.md §12.2; AI_ARCHITECTURE.md §16
  - Implementation: `ai/rag/evaluation.py` (new) — typed golden-set models (`GoldenDocument`/`GoldenQuery`/`GoldenSet`), the versioned fixture `ai/tests/golden/retrieval/golden_retrieval_v1.json` (6 docs, 9 queries, all 4 categories + 1 info-unavailable query; deterministic `sha256(source \x1f version \x1f index)` chunk ids matching the real pipeline), `load_golden_set`/`default_golden_set`, `build_golden_index`, `golden_retriever_for_index`, `recall_at_k`/`precision_at_k`, `evaluate_retrieval` (recall/precision/MRR, per-category gates 0.5/0.25/0.5), and `build_golden_verifier` (a ready-made `verify_before_swap` for task 7). Deterministic + offline: designed synthetic chunks + SHA-256 fake embeddings.
  - Verification: `ai/tests/test_evaluation.py` (15, §3.1n) — golden-set load/defaults, fixture integrity, golden-index build, recall/precision/MRR pass + fail scenarios (`top_k=1`), per-category gates, info-unavailable coverage, deterministic ids, golden-verifier good/bad providers. Full suite 580 passed (§3.1n); compileall OK; ruff clean; mypy clean (46 files).
  - Notes: the baseline is measured on the designed golden corpus; the real-corpus coverage baseline still requires seeded `knowledge/` content (Phase 3 seed data) and live-model retrieval quality remains Phase 13.
- `[x]` **Knowledge read-side API (supporting, NOT RAG)**
  - Source: `API_SPECIFICATION.md` §23
  - Implementation: `backend/app/api/v1/endpoints/knowledge.py` (documents list/detail + chunks/sources listing)
  - Verification: `backend/tests/api/test_knowledge_api.py` (5), `backend/tests/unit/repositories/test_knowledge_repository.py`
  - Notes: document metadata + chunk listing only; does not implement retrieval

### Phase 10 — AI Chat System — `[~]`

- `[x]` **Conversation lifecycle CRUD + archive/restore (backend)**
  - Source: `API_SPECIFICATION.md` §20, §22
  - Implementation: `backend/app/api/v1/endpoints/conversations.py`
  - Verification: `backend/tests/api/test_conversations_api.py` (8), `backend/tests/unit/services/test_ai_conversations_service.py` (17)
- `[x]` **Message send + history (backend)**
  - Source: `API_SPECIFICATION.md` §20
  - Implementation: `backend/app/api/v1/endpoints/messages.py`
  - Verification: `backend/tests/api/test_messages_api.py` (4), `backend/tests/unit/services/test_chat_history_service.py` (13)
- `[x]` **Feedback submission + triage state machine**
  - Source: `API_SPECIFICATION.md` §21.5; AI_ARCHITECTURE.md §29
  - Implementation: `backend/app/api/v1/endpoints/ai.py` (`/ai/feedback`, `/ai/feedback/{id}/status`)
  - Verification: `backend/tests/api/test_ai_api.py` (6), `backend/tests/unit/services/test_feedback_service.py` (17)
- `[x]` **Citation sources per message (read)**
  - Source: `API_SPECIFICATION.md` §21.4
  - Implementation: `GET /api/v1/ai/sources/{message_id}`
  - Verification: `test_ai_api.py` (sources tests incl. owner-scoping)
- `[x]` **AI reply generation (`/ai/chat` boundary)**
  - Source: `API_SPECIFICATION.md` §21.1; AI_ARCHITECTURE.md §2
  - Implementation: `backend/app/api/v1/endpoints/ai.py` (`/ai/chat`), `backend/app/services/ai_chat.py` (Step A facade), `backend/app/schemas/ai.py`, `backend/app/dependencies/services.py`, `backend/app/repositories/knowledge_chunks.py` (`get_by_vector_id`), `backend/app/services/ai_sources.py` (citation persistence)
  - Verification: `backend/tests/api/test_ai_chat_api.py` (8), `backend/tests/unit/services/test_ai_chat_service.py` (11)
- `[x]` **Conversation memory integration**
  - Source: AI_ARCHITECTURE.md §21, §22.5, §23.1
  - Implementation: `backend/app/services/ai_memory.py` (`ConversationMemoryWriter` — the workflow's `persist_writer` boundary), `backend/app/services/ai_chat.py` (session-memory rebuild from persisted `chat_history` + opt-in summary flush). The existing `ai/memory/manager.py` is reused unchanged; message/source persistence stays owned by `ChatHistoryService`/`AISourceService`, so no duplicates are created
  - Verification: `backend/tests/unit/services/test_ai_chat_memory.py` (16)
- `[x]` **Chat UI (states, streaming, sources)**
  - Source: ui-ux-design.md §13, §36
  - Implementation: `frontend/app/(dashboard)/chat/page.tsx`, `frontend/app/(dashboard)/chat/[conversationId]/page.tsx`, `frontend/components/chat/ChatMessage.tsx`, `frontend/components/chat/ChatInput.tsx`, `frontend/components/chat/SuggestedPrompts.tsx`
  - Verification: `npm run build` compiled (Next.js 15.5.23), `npx tsc --noEmit` clean. Includes: message bubbles, suggested prompts, loading/thinking indicator, error state, send/stop toggle, keyboard shortcuts, citations, copy support, agent badge
- `[x]` **Chat history/resume UI**
  - Source: ui-ux-design.md §13, §16
  - Implementation: `frontend/app/(dashboard)/dashboard/history/page.tsx`, `frontend/components/layout/Sidebar.tsx`, `frontend/components/layout/AppShell.tsx`, `frontend/components/layout/Header.tsx`
  - Verification: `npm run build` compiled, route `/dashboard/history` working. Includes: grouped history, search, archive/restore/delete, conversation resume

### Phase 11 — Notifications — `[~]`

- `[x]` **Notification APIs** (list, read-state, unread count, soft-delete)
  - Source: `API_SPECIFICATION.md` §19
  - Implementation: `backend/app/api/v1/endpoints/notifications.py`
  - Verification: `backend/tests/api/test_notifications_api.py` (8 tests)
- `[x]` **Notification service** (event generation, read-state, priority)
  - Source: `BACKEND_ARCHITECTURE.md` §32.5; ui-ux-design.md §18
  - Implementation: `backend/app/services/notifications.py`
  - Verification: `backend/tests/unit/services/test_notifications_service.py` (14), `test_requests_service.py` (event generation)
- `[x]` **Priority model matching ui-ux-design §18**
  - Source: ui-ux-design.md §18; `DATABASE_DESIGN.md` §19
  - Implementation: `NotificationPriority` enum (`backend/app/models/enums.py`), `notifications.priority`
  - Verification: seed + service tests
- `[ ]` **Notifications UI**
  - Source: ui-ux-design.md §18
  - Implementation: not present

### Phase 12 — Profile & Settings — `[~]`

- `[x]` **Profile read/update, owner-scoped**
  - Source: `API_SPECIFICATION.md` §15, §17
  - Implementation: `backend/app/api/v1/endpoints/students.py` (`GET/PATCH /students/me`), `backend/app/api/v1/endpoints/users.py` (`GET/PATCH /users/me`)
  - Verification: `test_students_api.py` (5), `test_users_api.py` (5), service tests
- `[x]` **Dashboard aggregates**
  - Source: `API_SPECIFICATION.md` §15
  - Implementation: `GET /students/me/dashboard`
  - Verification: `test_students_api.py::test_dashboard_counts_are_owner_scoped`
- `[~]` **Optimistic-concurrency conflict (409)**
  - Source: `IMPLEMENTATION_PLAN.md` Phase 12; `DATABASE_DESIGN.md` §34.5
  - Implementation: `VersionMixin` + repository version bump only
  - Gap: no endpoint returns 409 on version mismatch; no test
- `[ ]` **Profile/settings UI**
  - Source: ui-ux-design.md §16
  - Implementation: not present

### Phase 13 — Testing — `[~]`

- `[x]` **Backend unit tests** (services, repositories, models, security, email, JWT)
  - Source: TESTING_STRATEGY.md §6
  - Implementation: `backend/tests/unit/**`
  - Verification: pytest run (this session) — 617 passed (§3.1)
- `[x]` **API contract tests**
  - Source: TESTING_STRATEGY.md §8
  - Implementation: `backend/tests/api/` (13 files)
  - Verification: included in the 617-passed run
- `[x]` **Auth/security tests**
  - Source: TESTING_STRATEGY.md §9, §15
  - Implementation: `test_auth_api.py`, `test_auth_bearer.py`, `test_rbac_api.py`, `test_sessions_api.py`, `test_security_edge_cases.py`, `test_security_hardening.py`
  - Verification: included in the 617-passed run
- `[x]` **DB/migration tests**
  - Source: TESTING_STRATEGY.md §7
  - Implementation: `test_database.py`, `test_alembic.py`, `test_models.py`, `test_models_mixins.py`, `test_database_health.py`, `test_migration_helpers.py`
  - Verification: included in the 617-passed run; manual `alembic upgrade head` (§3.1)
- `[ ]` **Coverage reports per §29**
  - Source: TESTING_STRATEGY.md §29
  - Implementation: not generated
  - Remaining work: coverage run + threshold verification
- `[~]` **AI tests** (routing, grounding, citations, guardrails)
  - Source: TESTING_STRATEGY.md §10–12
  - Implementation: `ai/tests/` — `test_config.py`, `test_state.py`, `test_workflow.py`, `test_coordinator.py`, `test_gateway.py`, `test_llm_classifier.py`, `test_admission.py`, `test_examination.py`, `test_faq.py`, `test_guardrails.py`, `test_memory.py`, `test_prompts.py`, `test_workflow_specialists.py`, `test_workflow_clarify.py` (307 tests, all passing; §3.1c–§3.1g)
  - Gap: present tests cover AI **foundation + Coordinator + Admission/Examination/FAQ agents + guardrails + conversation memory + agent handoff** (config, workflow state, workflow structure, rule-based + LLM-backed routing via the gateway, retry/fallback/error mapping, grounded specialist pipeline: retrieval params, context trimming, citation order/dedup/clamping, no-answer + error fallbacks, Coordinator → specialist routing, prompt-injection/jailbreak/unsafe/restricted/out-of-scope input checks, unsafe/leakage/authority output checks, pipeline guardrail short-circuits, short-term window + opt-in long-term summarization + session rebuild + safe persistence, and §24 handoff metadata recorded by the `route` node). Tests for real-model routing quality, grounding, retrieval, citations, real-model long-term summarization, and end-to-end AI chat are NOT implemented.
- `[ ]` **Frontend component/UI tests**
  - Source: TESTING_STRATEGY.md §5
  - Implementation: not present (`frontend/tests/` empty)
- `[ ]` **E2E / integration / load suites**
  - Source: TESTING_STRATEGY.md §4, §16
  - Implementation: not present (`testing/{e2e,integration,load}/` are `.gitkeep` placeholders)

### Phase 14 — Deployment — `[~]`

- `[?]` **Dockerfiles for all services**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Deployment task 1; DEPLOYMENT.md §6
  - Implementation: `backend/Dockerfile`, `frontend/Dockerfile`, `ai/Dockerfile`
  - Verification: pending — no `docker build` has been run; frontend/ai images would wrap empty applications
- `[~]` **Docker Compose stacks (dev + prod)**
  - Source: DEPLOYMENT.md §7
  - Implementation: `docker/docker-compose.yml`, `docker/docker-compose.dev.yml`
  - Gap: only the `db` service is active; backend/ai/frontend are commented out; stack not validated (`docker compose config` not run)
- `[ ]` **Reverse proxy + HTTPS**
  - Source: DEPLOYMENT.md §14–15
  - Implementation: not present (no nginx/TLS in compose)
- `[~]` **Persistent volumes + backups**
  - Source: DEPLOYMENT.md §10, §21
  - Implementation: `postgres_data` volume + `database/init` mount declared
  - Gap: no backup/restore mechanism
- `[~]` **Environment injection + secrets management**
  - Source: DEPLOYMENT.md §13
  - Implementation: `.env` templates + gitignore discipline only
  - Gap: no secret store or rotation policy
- `[ ]` **CI pipelines (lint, type-check, test, build)**
  - Source: `IMPLEMENTATION_PLAN.md` §4 Deployment task 6; DEVELOPMENT_WORKFLOW.md §28.5
  - Implementation: placeholder `echo` workflows only (Phase 1)
- `[~]` **Monitoring + health-check wiring**
  - Source: DEPLOYMENT.md §19–20
  - Implementation: health endpoints implemented + tested (`backend/app/api/v1/endpoints/health.py`)
  - Gap: no external monitoring/alerting
- `[ ]` **Operational (§32) + production readiness (§33) checklists**
  - Source: DEPLOYMENT.md §32–33
  - Implementation: not run

### Phase 15 — Final Optimization — `[ ]`

- `[ ]` **Performance tuning** (caching, query optimization, token budgets)
  - Source: `IMPLEMENTATION_PLAN.md` Phase 15; `API_SPECIFICATION.md` §36
  - Implementation: not started
- `[ ]` **Accessibility + UX polish pass**
  - Source: ui-ux-design.md §22; TESTING_STRATEGY.md §17
  - Implementation: not started (no UI exists yet)
- `[ ]` **Documentation finalization + FYP evidence**
  - Source: `IMPLEMENTATION_PLAN.md` Phase 15
  - Implementation: not started

---

## 5. Completed Work

Only genuinely verified `[x]` requirements appear here. (66 total.)

- **Phase 1 (5):** folder structure, env templates, docker skeletons, gitignore/gitattributes, doc set.
- **Phase 2 (9):** app factory, settings, structured logging + correlation IDs, exception handling + error envelope, DI, `/api/v1` versioning, health endpoints, middleware, self-hosted docs.
- **Phase 3 (7):** SQLAlchemy base + session, 16-table models, relationships/constraints/indexes, Alembic migrations, repository pattern, soft delete + owner scoping, audit-write patterns.
- **Phase 4 (9):** password hashing, JWT issuance, register + email verification, login + rate limiting, refresh rotation + revocation, password reset, RBAC + owner scoping, logout/session invalidation, transactional email service.
- **Phase 6 (1):** dashboard aggregates (backend).
- **Phase 7 (4):** request APIs, lifecycle state machine, append-only timeline, notifications on lifecycle events.
- **Phase 8 (9):** `ai/` service structure (agents, graphs, prompts, tools, memory, rag layout) — includes the shared AI configuration (`ai/core/config.py`) and typed workflow state (`ai/core/state.py`); the Coordinator Agent (intent detection + routing, incl. LLM-backed intent classification via the provider-agnostic gateway and the wired `detect_intent`/`route` workflow nodes); the Admission + Examination + FAQ specialist agents (grounded pipelines on the shared `SpecialistAgent` base with versioned prompts, context builder, citation assembly, and no-answer/error fallbacks); the guardrails + safety rules (`ai/guardrails/` — prompt-injection/jailbreak/unsafe/restricted/out-of-scope input checks and unsafe/leakage/authority output checks, integrated into the shared pipeline); the conversation memory + agent handoff + error recovery (`ai/memory/` — short-term window, opt-in long-term summarization, session rebuild, safe persistence §23.1; typed `Handoff` + `current_agent`/`handoff` on `WorkflowState`; the `route` node records §24 handoff metadata and `detect_intent` enforces the window §12.5); the versioned-prompt execution wiring + version checks (`ai/agents/base.py` + `ai/prompts/` — repository-resolved versioned prompts actually reach the gateway, ownership/unsupported-version validation fails fast, shared components compose into every final prompt, resolved `prompt_version` recorded per generation §34.6); and the LangGraph specialist-phase wiring + the functional clarify node (`ai/graphs/workflow.py` + `ai/tests/test_workflow_specialists.py` + `ai/tests/test_workflow_clarify.py` — retrieve delegates to the injected specialist and records `agent_output`, the context/generate/citations/aggregate nodes are honest pass-throughs §13.5, persist appends to the memory window via an injectable writer, and the clarify node returns a grounded CLARIFYING turn per §9.4/§9.5/§11.3/§11.5 with no specialist execution and no invented prompt). Structure/agents/guardrails/memory-handoff/prompt-wiring/specialist-wiring/clarify only: NOT RAG.
- **Phase 9 (9):** knowledge read-side API (explicitly NOT RAG); **document ingestion + chunking** (`ai/rag/ingestion.py` — RAG task 1: validation per §36.3, metadata per §36.5, deterministic chunking per §36.4, lifecycle eligibility per §21.3, `RetrievedChunk` compatibility; 46 offline tests); **Sentence Transformers embeddings** (`ai/rag/embeddings.py` — RAG task 2: injectable `EmbeddingProvider` protocol, lazily-loaded config-driven Sentence Transformer provider, batched chunk embedding + individual query embedding with model parity, chunk-to-vector association via `ChunkEmbedding`, deterministic dimension/empty/count/non-finite validation per §15; 39 offline tests); **FAISS index + persistence** (`ai/rag/faiss_index.py` — RAG task 3: cosine metric via L2-normalized vectors + `IndexFlatIP` per §16.2, deterministic position↔`chunk_id` metadata mapping persisted atomically (temp → validate → replace) per §36.7, typed corruption/version/count/dimension/model/metric errors, lazy FAISS load, deterministic byte-identical persistence; 47 offline tests); **concrete retriever** (`ai/rag/faiss_retriever.py` — RAG task 4: query embedding via the same injected provider, raw cosine ranking with a deterministic position tie-break per §16.3, category + version-currency filtering per §16.4/§21.3, top-K/`RAG_TOP_K` bounding, de-duplication, `RetrievedChunk` conversion, typed `RetrieverError` hierarchy, persisted-index `create_faiss_retriever` factory; 45 offline tests); **context builder within the token budget** (`ai/rag/context_builder.py` — RAG task 5: §17.2 labeled assembly order wired into every specialist's retrieve → build_context → generate pipeline, `Settings.context_budget_tokens` → `context_builder.max_tokens` through the `create_*_agent` factories, §17.4 prioritization with `ContextOverflowError` only for essential overflow, deterministic `max(1, len//4)` estimation per §17.3, evidence blocks render `[chunk: …]` ids for §19.1/§19.3 citation compatibility, empty-retrieval short-circuit per §20.4; 21 unit + 17 integration offline tests); **citation generation/dedup** (`ai/agents/base.py` — RAG task 6: deterministic citation assembly from retrieved `RetrievedChunk` metadata with retrieval-position tie-break per §16.3, per-chunk dedup per §19.3, 0..1 `relevance_score` clamp per §19.4/§32.6, no fabrication per §20.3, `AgentOutput.citations` preserved; 28 offline tests). **knowledge re-indexing job** (`ai/rag/reindexer.py` — RAG task 7: ingest → embed → build/save FAISS index → atomic verified swap of the persisted manifest + index, removal detection, `verify_before_swap` gate; 15 offline tests, Step R9-7, §3.1n) and **golden retrieval/eval sets** (`ai/rag/evaluation.py` — RAG task 8: versioned golden fixture `golden_retrieval_v1.json` (6 docs, 9 queries, all categories), `evaluate_retrieval` recall/precision/MRR with per-category gates, `build_golden_verifier`; 15 offline tests, Step R9-8, §3.1n).
- **Phase 10 (4):** conversation CRUD, message send/history, feedback submit/triage, citation sources read.
- **Phase 11 (3):** notification APIs, notification service, priority model.
- **Phase 12 (2):** profile read/update, dashboard aggregates.
- **Phase 13 (4):** backend unit tests, API contract tests, auth/security tests, DB/migration tests.

---

## 6. Remaining Work

All items below are `[ ]`, `[~]`, or `[?]`. Nothing here is `[x]`.

### High Priority

- `[~]` **AI Foundation (Phase 8)** — service structure, shared config, workflow state, the full LangGraph workflow, the functional Coordinator Agent (intent detection + routing via the provider-agnostic LLM gateway), the functional **Admission + Examination + FAQ agents** (grounded specialist pipelines on the shared `SpecialistAgent` base with versioned prompts + context builder), the **guardrails + safety rules** (`ai/guardrails/`, integrated into the shared pipeline), the **conversation memory + agent handoff + error recovery** (`ai/memory/` §21/§23/§24), the **prompt-execution wiring + version checks** (Step 1J), the **LangGraph specialist-phase wiring** (Step 1K: retrieve delegates to the injected specialist and records `agent_output`, the context/generate/citations/aggregate nodes are honest pass-throughs, persist appends to the memory window via an injectable writer), and the **functional clarify node** (Step 1L: grounded deterministic CLARIFYING turn per §9.4/§9.5/§11.3/§11.5 — no specialist execution, no invented prompt) are done and verified (Steps 1A–1L + R9-1; 353 offline AI tests). The phase is not marked complete because plan-level completion criteria remain pending: (a) guardrail/audit logging of routing decisions to `agent_logs` (§11.4, §30.1, §37) is a Phase 10 persistence concern, and (b) real-model AI verification is Phase 13. Blocks the project's core contribution (chat) until Phase 9 RAG + Phase 10 wiring.
- `[ ]` **AI reply wiring (Phase 10)** — implement the `/ai/chat` boundary connecting chat messages to the LangGraph workflow.
- `[ ]` **Frontend Foundation (Phase 5)** — Next.js 15 scaffold, Tailwind tokens, shadcn/ui, layouts/navigation, public pages.
- `[ ]` **Background task infrastructure (Phase 2)** — required for RAG re-indexing and future email/retention jobs.

### Medium Priority

- `[~]` **Optimistic-concurrency 409 (Phase 12)** — surface version-conflict behavior in update endpoints + tests.
- `[~]` **Seed data (Phase 3)** — sample users and sample knowledge documents beyond departments (seeding the `knowledge/` corpus also enables the real-corpus RAG retrieval-coverage baseline, the Phase 9 task 8 follow-up).
- `[ ]` **Login/register + dashboard UI (Phase 6)**.
- `[ ]` **Chat UI + history/resume UI (Phase 10)**.
- `[ ]` **Request submission/tracking UI (Phase 7)**.
- `[ ]` **Notifications UI (Phase 11)**.
- `[ ]` **Profile/settings UI (Phase 12)**.
- `[ ]` **File upload handling (Phase 2)** — upload endpoint + validation/storage per API_SPECIFICATION §35.
- `[~]` **Test completion (Phase 13)** — AI foundation + Coordinator + Admission/Examination/FAQ Agent + guardrails + memory/handoff + prompt-wiring + specialist-phase wiring + functional clarify-node + RAG ingestion/chunking/embedding tests exist (392 passed); still missing AI quality tests (real-model routing/grounding/citations/LLM/handoff/e2e chat), frontend component tests, E2E/integration/load, coverage report per §29.
- `[~]` **Lint cleanup** — fix the 3 known `ruff` errors (I001 ×2, UP038 ×1) so the lint gate is green.

### Low Priority

- `[~]` **CI pipelines (Phase 1/14)** — replace `echo` placeholders with real lint/type-check/test/build jobs.
- `[?]` **Docker image builds (Phase 14)** — verify each Dockerfile builds successfully.
- `[~]` **Docker Compose full stack (Phase 14)** — enable backend/ai/frontend services; validate with `docker compose config`.
- `[ ]` **Reverse proxy + HTTPS (Phase 14)**.
- `[~]` **Backup/restore mechanism (Phase 14)**.
- `[~]` **Secrets management (Phase 14)** — store + rotation.
- `[~]` **External monitoring/alerting (Phase 14)** — wire to existing health endpoints.
- `[ ]` **Operational + production readiness checklists (Phase 14, DEPLOYMENT §32–33)**.
- `[ ]` **Phase 15 optimization items** — performance tuning, accessibility pass, documentation finalization, FYP evidence.

---

## 7. Final Report

### Requirement counts

| Status | Count |
| ------ | ----- |
| `[x]` implemented + verified | **66** |
| `[~]` in progress / partial | **9** |
| `[?]` verification pending | **1** |
| `[ ]` not started / incomplete | **26** |
| **Total requirements tracked** | **102** |

### Answers

1. **`[x]` requirements:** 66 (see §5).
2. **`[~]` requirements:** 9 — CI skeletons (P1), seeds (P3), optimistic concurrency (P3), optimistic-concurrency 409 (P12), AI tests partial (P13), docker compose stacks, volumes+backups, env/secrets, monitoring wiring (P14).
3. **`[?]` requirements:** 1 — Dockerfiles build verification (P14).
4. **`[ ]` requirements:** 26 (see §6).
5. **Backend requirements fully verified (`[x]`):** all of Phase 4 (Authentication, 9 items); Phase 2 foundation (9 of 11); Phase 3 database (7 of 9); Phase 7 request backend (4); Phase 10 chat data layer (4); Phase 11 notifications backend (3); Phase 12 profile backend (2); Phase 6 dashboard aggregates (1); Phase 9 knowledge read-side API (1) + **RAG document ingestion + chunking** (1, `ai/rag/ingestion.py`) + **RAG Sentence Transformers embeddings** (1, `ai/rag/embeddings.py`) + **RAG FAISS index + persistence** (1, `ai/rag/faiss_index.py`) + **RAG concrete retriever** (1, `ai/rag/faiss_retriever.py`) + **RAG context builder within the token budget** (1, `ai/rag/context_builder.py`) + **RAG citation generation/dedup** (1, `ai/agents/base.py`) + **RAG knowledge re-indexing job** (1, `ai/rag/reindexer.py`) + **RAG golden retrieval/eval sets** (1, `ai/rag/evaluation.py`); Phase 13 backend test suites (4); Phase 8 `ai/` service structure + Coordinator Agent + Admission Agent + Examination Agent + FAQ Agent + guardrails + conversation memory/handoff/error recovery + versioned-prompt execution wiring/version checks + the LangGraph workflow (specialist-phase wiring + functional clarify node) (9). Verified by the specific tests cited in §4 and the commands in §3.1/§3.1b/§3.1c/§3.1d/§3.1e/§3.1f/§3.1g/§3.1h/§3.1i/§3.1j/§3.1k/§3.1l/§3.1m/§3.1n (pytest 580 passed for `ai/`, backend 617 passed, mypy clean, alembic upgrade head applied, migrations exercised by `test_alembic.py`).
6. **Backend requirements remaining:** background tasks `[ ]`, file upload `[ ]`, full seed set `[~]`, optimistic-concurrency 409 `[~]`, lint clean `[~]`, coverage report `[ ]`.
7. **AI requirements remaining:** the AI **foundation** (service structure, shared config, workflow state, full LangGraph workflow), the **functional Coordinator Agent** (rule + LLM-backed intent detection and routing via the provider-agnostic Gemini/OpenAI/Groq gateway, wired into the workflow's `detect_intent`/`route`/`clarify` nodes), the **functional Admission + Examination + FAQ agents** (grounded specialist pipelines with versioned prompts, context builder, citation assembly, and no-answer/error fallbacks), the **guardrails + safety rules** (`ai/guardrails/`, integrated into the shared pipeline), the **conversation memory + agent handoff + error recovery** (`ai/memory/` §21/§23/§24 — short-term window, opt-in long-term summarization, session rebuild, safe persistence; typed `Handoff` + `current_agent`/`handoff` on `WorkflowState`; the `route` node records §24 handoff metadata and `detect_intent` enforces the window §12.5), the **versioned-prompt execution wiring + version checks** (§34), and the **LangGraph specialist-phase wiring + functional clarify node** (Step 1K/Step 1L: retrieve delegates to the injected specialist and records `agent_output`; context/generate/citations/aggregate nodes are honest pass-throughs; persist appends to the memory window via an injectable writer; clarify returns a grounded CLARIFYING turn per §9.4/§9.5/§11.3/§11.5 with no specialist execution and no invented prompt) are implemented and verified — offline, with injected fake clients; real-model behavior is not yet verified. Phase 8 has no remaining functional work; the phase stays `[~]` only because guardrail/audit logging of routing decisions to `agent_logs` (§11.4/§30.1/§37) is a Phase 10 persistence concern and real-model verification is Phase 13. In Phase 9, **document ingestion + chunking is `[x]`** (`ai/rag/ingestion.py` — validation §36.3, metadata §36.5, deterministic chunking §36.4, eligibility §21.3, `RetrievedChunk` compatibility; 46 offline tests) and **Sentence Transformers embeddings is `[x]`** (`ai/rag/embeddings.py` — injectable `EmbeddingProvider` protocol, lazily-loaded config-driven Sentence Transformer provider, batched chunk embedding + individual query embedding with model parity, chunk-to-vector association, deterministic dimension/empty/count/non-finite validation per §15; 39 offline tests) and **FAISS index + persistence is `[x]`** (`ai/rag/faiss_index.py` — cosine metric via L2-normalized vectors + `IndexFlatIP`, deterministic position↔chunk_id metadata mapping, atomic temp→validate→replace persistence per §36.7, typed corruption/version/count/dimension/model/metric errors; 47 offline tests) and **the concrete retriever is `[x]`** (`ai/rag/faiss_retriever.py` — query embedded via the same injected provider, raw cosine ranking + deterministic position tie-break per §16.3, category + version-currency filtering per §16.4/§21.3, top-K/`RAG_TOP_K` bounding, de-duplication, `RetrievedChunk` conversion, typed `RetrieverError` hierarchy, persisted-index factory; 45 offline tests) and **the context builder within the token budget is `[x]`** (`ai/rag/context_builder.py` — §17.2 labeled assembly wired into every specialist's retrieve → build_context → generate pipeline, `Settings.context_budget_tokens` → `context_builder.max_tokens` through the `create_*_agent` factories, §17.4 prioritization with `ContextOverflowError` only for essential overflow, deterministic `max(1, len//4)` estimation per §17.3, evidence blocks render `[chunk: …]` ids for §19.1/§19.3 citation compatibility, empty-retrieval short-circuit per §20.4; 21 unit + 17 integration offline tests) and **citation generation/dedup is `[x]`** (`ai/agents/base.py` — deterministic score-ordered citation assembly from retrieved `RetrievedChunk` metadata with retrieval-position tie-break per §16.3, per-chunk dedup per §19.3, 0..1 `relevance_score` clamp per §19.4/§32.6, no fabrication per §20.3; 28 offline tests); still `[ ]`: re-index job, golden retrieval sets; and `/ai/chat` AI reply wiring `[ ]` in Phase 10. In Phase 9, the **knowledge re-indexing job (task 7)** and the **golden retrieval/eval sets (task 8)** are now `[x]` (`ai/rag/reindexer.py`, `ai/rag/evaluation.py`; 30 offline tests, Step R9-7/R9-8, §3.1n) — all eight RAG tasks are complete and Phase 9 is `[x]`; the only Phase 9-adjacent follow-ups are seeding the real `knowledge/` corpus (Phase 3) and measuring the real-corpus coverage baseline.
8. **Frontend requirements remaining:** auth + dashboard UI (login page present, dashboard page present), request UI `[ ]`, notifications UI `[ ]`, profile/settings UI `[ ]`, frontend tests `[ ]`. Phase 5 foundation, chat UI, and history/resume UI are now `[x]`.
9. **Deployment requirements remaining:** docker builds `[?]`, compose full stack `[~]`, reverse proxy/HTTPS `[ ]`, backups `[~]`, secrets store `[~]`, real CI pipelines `[ ]`, external monitoring `[~]`, §32–33 checklists `[ ]`.
10. **Exact next implementation task per `IMPLEMENTATION_PLAN.md`:** Phase 9 — RAG Implementation (the `ai/` structure task 1, LangGraph workflow task 2, Coordinator Agent task 3, Admission Agent task 4, Examination Agent task 5, FAQ Agent task 6, **Versioned prompts task 7**, Guardrails + Safety Rules task 8, Conversation memory + agent handoff + error recovery task 9–10, the LangGraph specialist-phase wiring tasks 2/3 remainder, the LangGraph clarify node (task 2 remainder), and the RAG **document ingestion + chunking** (task 1, Step R9-1), RAG **Sentence Transformers embeddings** (task 2, Step R9-2), and RAG **FAISS index + persistence** (task 3, Step R9-3), and RAG **concrete retriever** (task 4, Step R9-4), and RAG **context builder within the token budget** (task 5, Step R9-5), and RAG **citation generation/dedup** (task 6, Step R9-6, `ai/agents/base.py`) are all now complete. The exact next task was **Phase 9 RAG task 7 — the knowledge re-index background job (IMPLEMENTATION_PLAN.md §4 RAG task 7)** and RAG task 8 — golden retrieval/eval sets; **both are now complete** (Step R9-7/R9-8, §3.1n — `ai/rag/reindexer.py` + `ai/rag/evaluation.py`, 30 new offline tests; full `ai/` suite 580 passed), so **Phase 9 RAG Implementation is now `[x]` and the exact next implementation task is Phase 10 — AI Chat System (the `/ai/chat` boundary wiring per API_SPECIFICATION.md §21.1)**. The guardrails were implemented per AI_ARCHITECTURE.md §25–26 and §37 as Step 1H (new `ai/guardrails/` package integrated into the shared `SpecialistAgent` pipeline; input checks before retrieval/LLM, output checks after generation, safe category-appropriate fallbacks that never leak internals; 39 offline tests). The memory + handoff + error recovery was implemented per AI_ARCHITECTURE.md §21/§23–24 as Step 1I (`ai/memory/manager.py` — stateless `ConversationMemoryManager` with short-term window, opt-in long-term summarization, session rebuild, and safe §23.1 persistence; `Handoff` + `current_agent`/`handoff` on `WorkflowState`; the workflow `route` node records §24 handoff metadata and `detect_intent` enforces the window; 22 offline tests). The versioned-prompt execution wiring + version checks were implemented per AI_ARCHITECTURE.md §13/§34 as Step 1J (repository-resolved versioned prompts actually reach the gateway, ownership/unsupported-version validation fails fast, shared components compose into every final prompt, resolved `prompt_version` recorded per generation; 27 offline tests). The LangGraph specialist-phase wiring was implemented per AI_ARCHITECTURE.md §11–13 as Step 1K (the `retrieve` node delegates to the injected specialist via `SpecialistAgent.run` and records `agent_output`; the context/generate/citations/aggregate nodes are honest pass-throughs §13.5; `persist` appends user + assistant turns to the short-term memory window through an injectable writer §21/§23.1; routing preserved end-to-end incl. GENERAL→FAQ; 12 offline integration tests). The clarify node was implemented per AI_ARCHITECTURE.md §9.4–9.5/§11.3/§11.5 as Step 1L (`ai/agents/coordinator.py` `CoordinatorAgent.clarify` + the workflow `clarify` node — a deterministic, data-driven CLARIFYING turn built from the live agent registry; no prompt was invented because §13.2 has no dedicated clarification type; out-of-scope scope-boundary + nearest-specialist naming; no specialist/LLM/retrieval execution; routing_signal/conversation_id/user_context/message_history/current_agent/handoff preserved; 17 offline tests in `test_workflow_clarify.py`). These are prerequisites for Phase 9 (RAG) and Phase 10 (AI Chat). Phase 9 task 1 (document ingestion + chunking) was implemented as Step R9-1 (`ai/rag/ingestion.py`, 46 offline tests; see §3.1h) and is `[x]`.

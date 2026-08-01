# API_SPECIFICATION.md

**Agentic AI-Based University Workflow Automation System**
Multi-Agent Student Support Platform — developed for **Sindh Madressatul Islam University (SMIU)**

> Version: 1.0 · Status: Approved Architecture · Last Updated: August 2026 · Owner: Final Year Project Team
> Scope: Single source of truth for every backend API endpoint — standards, conventions, authentication, request/response contracts, endpoint catalog, error strategy, security, and lifecycle.
> Sufficiently detailed that the entire REST API can be generated without additional API instructions.
> This document is **documentation only** — it contains no FastAPI code, no Python code, no SQL, no JSON schema, no OpenAPI YAML, and no pseudocode.

---

## Table of Contents

1. [API Standards](#1-api-standards)
2. [REST Conventions](#2-rest-conventions)
3. [Authentication](#3-authentication)
4. [Authorization](#4-authorization)
5. [JWT Flow](#5-jwt-flow)
6. [Request Format](#6-request-format)
7. [Response Format](#7-response-format)
8. [Error Format](#8-error-format)
9. [Pagination](#9-pagination)
10. [Filtering](#10-filtering)
11. [Sorting](#11-sorting)
12. [Validation Rules](#12-validation-rules)
13. [Rate Limiting](#13-rate-limiting)
14. [API Versioning](#14-api-versioning)
15. [Student APIs](#15-student-apis)
16. [Authentication APIs](#16-authentication-apis)
17. [User APIs](#17-user-apis)
18. [Request APIs](#18-request-apis)
19. [Notification APIs](#19-notification-apis)
20. [Chat APIs](#20-chat-apis)
21. [AI APIs](#21-ai-apis)
22. [Conversation APIs](#22-conversation-apis)
23. [Knowledge Base APIs](#23-knowledge-base-apis)
24. [Health Check APIs](#24-health-check-apis)
25. [Admin APIs (Future)](#25-admin-apis-future)
26. [Error Codes](#26-error-codes)
27. [HTTP Status Codes](#27-http-status-codes)
28. [Security Rules](#28-security-rules)
29. [API Naming Convention](#29-api-naming-convention)
30. [OpenAPI Documentation Rules](#30-openapi-documentation-rules)
31. [Example JSON Requests](#31-example-json-requests)
32. [Example JSON Responses](#32-example-json-responses)
33. [API Lifecycle Management](#33-api-lifecycle-management)
34. [Idempotency Rules](#34-idempotency-rules)
35. [File Upload APIs](#35-file-upload-apis)
36. [API Performance Standards](#36-api-performance-standards)
37. [API Monitoring & Logging](#37-api-monitoring--logging)
38. [API Testing Strategy](#38-api-testing-strategy)
39. [Future API Expansion](#39-future-api-expansion)

---

## 1. API Standards

### 1.1 API Philosophy

The API is the **single programmatic boundary** between the Next.js frontend, the FastAPI backend, and the AI service. It is RESTful, JSON-only, versioned, and documented via OpenAPI. It follows the layered architecture of **docs/architecture/BACKEND_ARCHITECTURE.md**: thin routers → services → repositories → database, with the AI layer reachable only through services.

### 1.2 REST Principles

| Principle | Commitment |
| --------- | ---------- |
| Resource-based | Everything is modeled as a resource (users, requests, conversations, notifications) |
| Uniform interface | Fixed set of HTTP methods with semantic meaning (Section 2.2) |
| Stateless | No client session state on the server; every request is self-contained |
| Representational | Resources are represented as JSON and fully described by their representation |
| Layered | Clients talk to the API only; no direct database or AI-layer access |
| HATEOAS-ready | Links are included in responses where they aid navigation (non-binding) |

### 1.3 JSON Communication

- **All** requests and responses use `application/json` (except file uploads — `multipart/form-data`, Section 35).
- Field names are `snake_case` (Section 29).
- Responses are structured, typed, and validated with Pydantic v2 (BACKEND_ARCHITECTURE.md §14).

### 1.4 HTTPS Requirements

- HTTPS is mandatory in every environment except local development.
- HTTP requests in production are redirected or rejected; HSTS headers are set (Section 28).
- All traffic between frontend ↔ API ↔ AI service is encrypted in transit.

### 1.5 Stateless Architecture

- The API nodes are stateless: any instance can serve any request (BACKEND_ARCHITECTURE.md §23).
- Authentication state lives in JWTs + server-side sessions (DATABASE_DESIGN.md §25); no sticky sessions.
- Horizontal scaling requires no session affinity.

### 1.6 Naming Consistency

- Endpoints: `kebab-case`, nouns, plural resource roots (PROJECT_RULES.md).
- JSON fields: `snake_case`.
- Errors: consistent envelope with stable error codes (Section 8).
- Collections, members, actions, and parameters follow the conventions in Section 29.

### 1.7 API Design Principles

| Principle | Meaning |
| --------- | ------- |
| Thin routers | Routers validate and delegate; no business logic (BACKEND_ARCHITECTURE.md §11) |
| Explicit contracts | Every endpoint documents its request/response schema |
| Least privilege | Every endpoint authenticates and authorizes (Sections 3–4) |
| Backward compatible | Breaking changes require a version or deprecation (Sections 14, 33) |
| Consistent errors | One error envelope everywhere (Section 8) |
| Production ready | Typed, validated, rate-limited, logged, and tested |

---

## 2. REST Conventions

### 2.1 Resource Naming

| Rule | Example |
| ---- | ------- |
| Plural nouns for collections | `/api/v1/requests`, `/api/v1/notifications` |
| Singular noun for a member | `/api/v1/requests/{request_id}` |
| Kebab-case for multi-word names | `/api/v1/request-timeline` |
| No verbs in resource paths | `/requests` (not `/getRequests`) |
| Actions as explicit sub-resources | `/api/v1/requests/{id}/submit` |

### 2.2 HTTP Methods

| Method | Semantics | Typical use |
| ------ | --------- | ----------- |
| `GET` | Read a collection or member | List requests, get profile |
| `POST` | Create a resource or trigger an action | Create request, login |
| `PUT` | Replace a resource (full) | Update settings (full) |
| `PATCH` | Partial update | Update profile fields |
| `DELETE` | Delete a resource | Delete conversation |

### 2.3 URI Design

| Pattern | Example |
| ------- | ------- |
| Base | `/api/v1` |
| Collection | `GET /api/v1/requests` |
| Member | `GET /api/v1/requests/{id}` |
| Sub-collection | `GET /api/v1/requests/{id}/timeline` |
| Action | `POST /api/v1/requests/{id}/submit` |
| Self | `/api/v1/users/me`, `/api/v1/students/me` |

### 2.4 Nested Resources

- Nested paths are used only for **owned sub-resources** (e.g., a request's timeline).
- Depth is limited to two levels; deeper data is fetched by reference.
- Collection resources that are filterable by parent are exposed at the top level with a filter parameter where simpler (e.g., `/api/v1/conversations?user_id=me`).

### 2.5 Idempotency

| Method | Idempotent | Rule |
| ------ | ---------- | ---- |
| `GET` | Yes | Repeatable without side effects |
| `PUT` | Yes | Full replace — repeated calls produce the same state |
| `DELETE` | Yes | Repeated delete returns success or a stable 404 |
| `POST` | No | Made idempotent via the `Idempotency-Key` header where required (Section 34) |
| `PATCH` | Best-effort | Partial updates; duplicate handling via `version` (optimistic locking) |

### 2.6 Standard Endpoint Patterns

| Pattern | Purpose |
| ------- | ------- |
| `GET /{resource}` | List with pagination/filter/sort (Sections 9–11) |
| `POST /{resource}` | Create |
| `GET /{resource}/{id}` | Read one |
| `PATCH /{resource}/{id}` | Partial update |
| `DELETE /{resource}/{id}` | Soft delete (Section 26 of DATABASE_DESIGN.md) |
| `POST /{resource}/{id}/{action}` | State transition / action |
| `GET /{resource}/me` | Current authenticated subject |

---

## 3. Authentication

### 3.1 JWT Authentication

- The API uses **JWT bearer tokens** for authentication (PROJECT_RULES.md, BACKEND_ARCHITECTURE.md §9).
- Access tokens are short-lived (default 60 minutes) and stateless.
- Refresh tokens are long-lived, server-side records, stored **hashed** (DATABASE_DESIGN.md §25).

### 3.2 Bearer Token

- Authenticated requests send `Authorization: Bearer <access_token>`.
- Tokens are sent in headers only — **never** in URLs, query strings, or bodies (ui-ux-design.md §33).
- Missing/invalid/expired tokens produce `401` with the standard error envelope.

### 3.3 Login Flow

1. Client posts credentials to `POST /api/v1/auth/login`.
2. Server validates credentials; issues access + refresh tokens; records a session (DATABASE_DESIGN.md §25).
3. Client stores the access token in memory and the refresh token in secure storage.
4. Client attaches the access token to subsequent requests.

### 3.4 Logout Flow

1. Client posts `POST /api/v1/auth/logout` with the refresh token.
2. Server revokes the session (`revoked_at`), invalidating the refresh token.
3. The client discards local tokens.

### 3.5 Token Validation

- The server verifies signature, issuer, audience, and expiry of every access token.
- Expired access tokens are rejected; the client uses the refresh flow (Section 5.4).
- Role and identity are derived from the verified token — never from client input (BACKEND_ARCHITECTURE.md §10.1).

---

## 4. Authorization

### 4.1 Role-Based Access Control (RBAC)

| Role | Phase | Access |
| ---- | ----- | ------ |
| **Student** | Phase 1 | Own profile, requests, conversations, notifications, AI chat |
| **Admin** | Future | All students, departments, knowledge base, agents, requests, analytics, settings |
| **Faculty** | Future | Read-only / department-scoped support |

- Enforcement is **server-side only** (BACKEND_ARCHITECTURE.md §10); frontend navigation visibility is informational.
- Deny by default; access is granted explicitly per route.

### 4.2 Student Permissions

| Capability | Endpoints |
| ---------- | --------- |
| Own profile & settings | `users/me`, `students/me` |
| Own requests | `requests/*` (scoped to owner) |
| Own conversations & messages | `conversations/*`, `chat/*` |
| Own notifications | `notifications/*` |
| AI chat & feedback | `ai/*` |
| Knowledge search | `knowledge/search` |

### 4.3 Future Admin Permissions

| Capability | Endpoints |
| ---------- | --------- |
| Manage students | `admin/students/*` |
| Manage departments | `admin/departments/*` |
| Manage knowledge base | `admin/knowledge/*` |
| Monitor agents | `admin/agents/*` |
| Manage all requests | `admin/requests/*` |
| Analytics & reports | `admin/analytics`, `admin/reports` |
| System settings | `admin/settings` |

### 4.4 Protected Endpoints

- Every endpoint except public auth endpoints, health checks, and knowledge search requires `get_current_user` (BACKEND_ARCHITECTURE.md §8.4).
- Admin endpoints additionally require the admin role.
- Authorization failures: `401` (unauthenticated) / `403` (forbidden).

---

## 5. JWT Flow

### 5.1 Token Creation

| Token | Contents | Lifetime |
| ----- | -------- | -------- |
| **Access token** | `sub` (user id), `role`, `jti`, `iat`, `exp` | Short (default 60 min) |
| **Refresh token** | `jti`, `sub` (user id), session binding | Long (default 7 days) |

- Access tokens are signed with the `JWT_SECRET` using the configured algorithm (default `HS256`).
- Refresh tokens are issued to the client once and stored server-side **hashed** (DATABASE_DESIGN.md §25).

### 5.2 Token Validation

- Signature, issuer, audience, and expiry are verified on every request.
- Access tokens are validated statelessly (no DB hit); sessions are validated on refresh.
- A `jti` identifies the token for revocation and replay detection.

### 5.3 Token Expiration

- Access tokens expire per `ACCESS_TOKEN_EXPIRE_MINUTES`; clients refresh before expiry.
- Refresh tokens expire per `REFRESH_TOKEN_EXPIRE_DAYS` and are revoked on logout/password change.
- Expired/revoked sessions fail cleanly with `AUTH`-scoped errors (Section 26).

### 5.4 Refresh Strategy

1. Client presents the refresh token to `POST /api/v1/auth/refresh`.
2. Server verifies the session (hash match, not expired, not revoked).
3. Server rotates: revokes the old session, issues a new refresh token + new access token, records `replaced_by_session_id` (rotation/replay detection).
4. Reused or replayed refresh tokens are detected and the entire session chain is revoked.

### 5.5 Logout Strategy

- Logout revokes the server-side session and its refresh token.
- Password change revokes all sessions for the account.
- Clients must discard local tokens on `401` and re-authenticate.

---

## 6. Request Format

### 6.1 Headers

| Header | Required | Purpose |
| ------ | -------- | ------- |
| `Authorization` | On protected routes | `Bearer <access_token>` |
| `Content-Type` | On bodies | `application/json` (or `multipart/form-data` for uploads) |
| `Accept` | Recommended | `application/json` |
| `Idempotency-Key` | On state-changing POSTs | Duplicate prevention (Section 34) |
| `X-Correlation-Id` | Recommended | Cross-service tracing (Section 37) |

### 6.2 Query Parameters

| Pattern | Example |
| ------- | ------- |
| Pagination | `?page=2&limit=20` |
| Filtering | `?status=in_review&department_id=...` |
| Search | `?q=admission` |
| Sorting | `?sort=-created_at` |
| Field selection (future) | `?fields=id,title,status` |

### 6.3 Path Parameters

- Path parameters identify a member: `/api/v1/requests/{request_id}`.
- Parameters are **UUIDs** (validated, Section 12.3) or stable identifiers (`me`).
- Unknown/invalid UUIDs return `404` (resource not found) or `422` (invalid format).

### 6.4 Request Body

- JSON bodies are validated by Pydantic v2 schemas at the boundary (BACKEND_ARCHITECTURE.md §14).
- Bodies are typed per endpoint; unknown fields are rejected by default (strict mode) or explicitly ignored — the policy is per-endpoint and documented.
- File uploads use `multipart/form-data` (Section 35).

### 6.5 Content Types

| Type | Use |
| ---- | --- |
| `application/json` | Default for all JSON APIs |
| `multipart/form-data` | File uploads (Section 35) |
| `text/event-stream` | Future streaming AI responses (Section 39) |

---

## 7. Response Format

### 7.1 Standard Envelope

Every response uses a consistent envelope so clients can rely on a single shape:

| Field | Type | Always present | Purpose |
| ----- | ---- | -------------- | ------- |
| `success` | boolean | Yes | Operation outcome |
| `data` | object / array / null | Yes | Payload |
| `meta` | object | Yes | Metadata (request id, timestamps, pagination) |

### 7.2 Success Response

| Field | Contents |
| ----- | -------- |
| `success` | `true` |
| `data` | The resource representation(s) |
| `meta.request_id` | Correlation id for tracing |
| `meta.timestamp` | UTC server timestamp |
| `meta.pagination` | Present on collection responses (Section 9) |

### 7.3 Error Response

| Field | Contents |
| ----- | -------- |
| `success` | `false` |
| `error.code` | Stable application error code (Section 26) |
| `error.message` | Human-readable message |
| `error.details` | Optional field-level detail array |
| `meta` | Request id, timestamp |

### 7.4 Metadata

- `meta` carries operational metadata (request id, timestamp) and, for collections, pagination (Section 9).
- Metadata never contains secrets or PII.

### 7.5 Pagination Metadata

Collection responses embed pagination in `meta.pagination` (Section 9): page, limit, offset, total, total_pages, next_page, prev_page.

---

## 8. Error Format

### 8.1 Error Structure

```text
success:  false
error:
  code:     AUTH001           (stable application code, Section 26)
  message:  Human-readable summary
  details:  [ field, reason ]  (validation detail; optional)
meta:
  request_id: correlation id
  timestamp:  UTC timestamp
```

### 8.2 Validation Errors

- HTTP `422` with field-level `details` (field name + reason).
- Generated by Pydantic v2 schema validation at the boundary.

### 8.3 Authentication Errors

- HTTP `401` with `AUTH`-scoped codes (missing, invalid, expired tokens).
- Login failures return a generic message to avoid account enumeration.

### 8.4 AI Errors

- HTTP `502`/`503` with `AI`-scoped codes (LLM unavailable, timeout, retrieval failure, generation error).
- The client always receives a friendly message; full details stay in server logs (Section 15 of BACKEND_ARCHITECTURE.md).

### 8.5 Server Errors

- HTTP `500` for unexpected errors — generic message, full detail logged.
- Stack traces are **never** exposed to clients.

---

## 9. Pagination

### 9.1 Parameters

| Parameter | Default | Rule |
| --------- | ------- | ---- |
| `page` | 1 | 1-based page index |
| `limit` | 20 | Max page size (configurable, hard capped) |
| `offset` | Computed | `(page - 1) * limit` |

### 9.2 Response Metadata

| Field | Meaning |
| ----- | ------- |
| `page` | Current page |
| `limit` | Page size used |
| `offset` | Starting index of the page |
| `total` | Total matching records |
| `total_pages` | `ceil(total / limit)` |
| `next_page` | Next page number, or `null` |
| `prev_page` | Previous page number, or `null` |

### 9.3 Rules

- Keyset pagination on indexed columns is preferred for large collections (DATABASE_DESIGN.md §31); page/offset is the public contract.
- Order is deterministic via the sort clause (Section 11).
- Oversized `limit` requests are capped, not rejected.

---

## 10. Filtering

### 10.1 Conventions

- Filters are query parameters in `snake_case`.
- Multiple filters combine with **AND** logic.
- Filtering is applied server-side; clients never receive unfiltered datasets.

### 10.2 Filter Types

| Type | Parameter example | Behavior |
| ---- | ----------------- | -------- |
| **Search** | `?q=admission` | Text search across indexed fields |
| **Date** | `?created_from=2026-01-01&created_to=2026-12-31` | Inclusive range on timestamps |
| **Status** | `?status=in_review` | Enumerated status filter (validated against the enum, Section 26 of DATABASE_DESIGN.md) |
| **Department** | `?department_id={uuid}` | Foreign-key filter |
| **Boolean** | `?is_active=true` | Boolean flags (`is_active`, `read`, ...) |
| **Type/priority** | `?request_type=admission&priority=high` | Enum filters |

### 10.3 Rules

- Invalid enum values return `422` validation errors.
- Unknown filter parameters are ignored or rejected per endpoint policy (documented).
- Filters on collection endpoints never bypass the owner-scope filter (Section 4.2).

---

## 11. Sorting

### 11.1 Conventions

- `?sort=field` ascending; `?sort=-field` descending.
- Multiple fields: comma-separated, applied in order — `?sort=-priority,created_at`.
- Only whitelisted, indexed fields are sortable (DATABASE_DESIGN.md §31).

### 11.2 Rules

| Rule | Detail |
| ---- | ------ |
| Ascending | Default; `sort=created_at` |
| Descending | Prefix `-`; `sort=-created_at` |
| Multiple fields | `sort=-priority,created_at` (priority desc, then created asc) |
| Default sorting | Defined per endpoint (e.g., requests by `-created_at`, notifications by `-created_at`) |
| Validation | Non-whitelisted fields produce `422` |

---

## 12. Validation Rules

### 12.1 Required vs Optional

| Rule | Detail |
| ---- | ------ |
| Required fields | Rejected with `422` + field detail if missing or empty |
| Optional fields | Explicitly nullable; validated when present |
| Strict bodies | Unknown fields handled per endpoint policy (documented) |

### 12.2 Field Validation

| Field | Rule |
| ----- | ---- |
| **UUID** | Valid RFC 4122 UUID required for all id parameters |
| **Email** | RFC-valid, length-capped, stored case-insensitively |
| **Password** | Minimum length (8+), strength policy at registration/reset |
| **Names/text** | Length caps per schema; no control characters |
| **Enums** | Must match the domain enum (status, priority, type) |
| **Dates/timestamps** | ISO 8601 UTC |
| **Numbers** | Bounds enforced (e.g., rating 1–5, cgpa 0–4) |

### 12.3 UUID Validation

- Path and body UUIDs are validated for format; unknown valid UUIDs return `404`.
- `me` is a reserved alias for the authenticated user's id.

### 12.4 Email Validation

- Format + length validated; uniqueness enforced (DATABASE_DESIGN.md §12).
- Case-insensitive storage via `citext`.

### 12.5 Password Validation

- Registration/reset enforce minimum length and complexity policy.
- Passwords are hashed; plaintext never stored, logged, or returned (Section 28).

### 12.6 File Validation

- Uploads validate MIME type, extension, size, and content (Section 35).

---

## 13. Rate Limiting

### 13.1 Limits

| Endpoint class | Default limit | Scope |
| -------------- | ------------- | ----- |
| **AI endpoints** (`/ai/*`) | Tight per-user limit (e.g., 10/min) | Per authenticated user |
| **Authentication endpoints** (`/auth/*`) | Tight per-IP limit (e.g., 5/min) | Per IP (brute-force protection) |
| **General APIs** | Moderate limit (e.g., 60/min) | Per user / IP |
| **Health checks** | Unrestricted or generous | Operators/monitoring |

### 13.2 Retry Behavior

- On `429`, clients honor the `Retry-After` header (Section 27).
- The UI shows a friendly rate-limit notice with countdown (ui-ux-design.md §36).
- Backoff is bounded; repeated abuse escalates to blocking + audit.

### 13.3 Rate Limit Responses

- HTTP `429` with the standard error envelope (`SYS`/`RATE`-scoped code).
- Headers may expose remaining quota (`X-RateLimit-*`) — documented, non-sensitive.

---

## 14. API Versioning

### 14.1 URL Versioning

- Version is part of the URL path: `/api/v1/...` (PROJECT_RULES.md API Standards).
- The current version is `v1`; future versions use `v2`, `v3`, ...

### 14.2 Future Versions

- A new version is created only for breaking changes (Section 33).
- Coexisting versions are supported during transition; old versions follow the deprecation policy.

### 14.3 Backward Compatibility

| Rule | Detail |
| ---- | ------ |
| Additive changes | New fields/endpoints under `v1` without breaking existing clients |
| Breaking changes | New version + deprecation timeline (Section 33.4) |
| Default version | `v1` is served at `/api/v1`; no unversioned default |
| Client guidance | Clients pin the version and migrate within the sunset window |

---

## 15. Student APIs

Student-related endpoints expose the authenticated student's academic profile and activities.

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/students/me` | Fetch the current student profile (1:1 with `users`, DATABASE_DESIGN.md §13) |
| `PATCH` | `/api/v1/students/me` | Update editable academic profile fields |
| `GET` | `/api/v1/students/me/dashboard` | Dashboard aggregates (active requests, pending, resolved, unread notifications) |

**Responsibility:** serve the authenticated student only; data is scoped by the owner (Section 4.2). Academic identity (department, program, semester) feeds AI context (AI_ARCHITECTURE.md §10.3).

---

## 16. Authentication APIs

Public authentication endpoints (no bearer token required).

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/api/v1/auth/register` | Create a student account (validate → hash password → create unverified account → trigger email verification) |
| `POST` | `/api/v1/auth/login` | Validate credentials → issue access + refresh tokens → record session |
| `POST` | `/api/v1/auth/logout` | Revoke the session/refresh token |
| `POST` | `/api/v1/auth/refresh` | Rotate the refresh token → issue a new access token |
| `POST` | `/api/v1/auth/verify-email` | Verify a signed email-verification token |
| `POST` | `/api/v1/auth/forgot-password` | Send a signed password-reset link |
| `POST` | `/api/v1/auth/reset-password` | Set a new password with a valid reset token; revoke existing sessions |

**Flow contract:** registration → email verification → login → refresh → logout (BACKEND_ARCHITECTURE.md §9.3). Rate-limited (Section 13). Password change additionally revokes all sessions.

---

## 17. User APIs

Authenticated user-profile and account endpoints.

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/users/me` | Fetch the authenticated user profile |
| `PATCH` | `/api/v1/users/me` | Update profile fields (name, phone, avatar) |
| `GET` | `/api/v1/users/me/settings` | Fetch user settings/preferences |
| `PUT` | `/api/v1/users/me/settings` | Replace settings (idempotent, full update) |
| `POST` | `/api/v1/users/me/change-password` | Change password (requires current password; revokes other sessions) |
| `GET` | `/api/v1/users/me/sessions` | List active sessions (devices) |
| `DELETE` | `/api/v1/users/me/sessions/{session_id}` | Revoke a specific session |

**Responsibility:** self-service account management; every route is owner-scoped (DATABASE_DESIGN.md §30).

---

## 18. Request APIs

Workflow request endpoints (DATABASE_DESIGN.md §17–18; BACKEND_ARCHITECTURE.md §32).

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/requests` | List own requests (paginated, filterable, sortable) |
| `POST` | `/api/v1/requests` | Create a request (draft or submitted; from portal or chat escalation) |
| `GET` | `/api/v1/requests/{request_id}` | Fetch request details (status, priority, department, timeline) |
| `PATCH` | `/api/v1/requests/{request_id}` | Update editable request fields (owner scope, optimistic lock) |
| `DELETE` | `/api/v1/requests/{request_id}` | Soft-delete a request (drafts/own requests only) |
| `POST` | `/api/v1/requests/{request_id}/submit` | Transition a draft to `submitted` |
| `GET` | `/api/v1/requests/{request_id}/timeline` | Fetch the append-only status timeline |
| `GET` | `/api/v1/requests/history` | Request history (resolved/closed/rejected) |

**Status model:** `draft → submitted → in_review → assigned → processing → resolved/closed/rejected` (ui-ux-design.md §17). Transitions are logged in `request_timeline`; ownership is student-scoped.

---

## 19. Notification APIs

Notification endpoints (DATABASE_DESIGN.md §19; ui-ux-design.md §18).

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/notifications` | List own notifications (paginated, filter by type/priority/read) |
| `POST` | `/api/v1/notifications/{notification_id}/read` | Mark one notification as read |
| `POST` | `/api/v1/notifications/read-all` | Mark all own notifications as read |
| `GET` | `/api/v1/users/me/notification-preferences` | Fetch notification preferences |
| `PUT` | `/api/v1/users/me/notification-preferences` | Update notification preferences |

**Priority model:** critical / high / medium / low drives badge color and ordering (ui-ux-design.md §18). Notifications are generated by workflow events, never ad hoc (BACKEND_ARCHITECTURE.md §32.5).

---

## 20. Chat APIs

Chat conversation endpoints — the student-facing AI chat surface (ui-ux-design.md §13).

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/api/v1/conversations` | Create a new conversation (with optional first message / department origin) |
| `POST` | `/api/v1/conversations/{id}/messages` | Send a message in the conversation |
| `GET` | `/api/v1/conversations/{id}/messages` | Fetch the conversation message history |
| `DELETE` | `/api/v1/conversations/{id}` | Delete (soft) a conversation |
| `PATCH` | `/api/v1/conversations/{id}` | Rename / update a conversation (title, summary) |

**Message lifecycle:** message states (sending, streaming, completed, error, stopped) per ui-ux-design.md §36; message persistence in `chat_history` (DATABASE_DESIGN.md §16). Message-send uses an idempotency key for duplicate prevention (Section 34).

---

## 21. AI APIs

AI endpoints — the agentic workflow boundary (AI_ARCHITECTURE.md §2).

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/api/v1/ai/chat` | Ask the AI: Coordinator routing → specialist → RAG → grounded response + citations |
| `POST` | `/api/v1/ai/stream` | Future: streaming AI responses (SSE, Section 39) |
| `POST` | `/api/v1/ai/feedback` | Submit feedback for an AI message (rating/comment/flag, DATABASE_DESIGN.md §23) |
| `GET` | `/api/v1/ai/sources/{message_id}` | Retrieve the citation sources for a message (DATABASE_DESIGN.md §22) |

### 21.1 Ask AI (request contract)

| Field | Purpose |
| ----- | ------- |
| `conversation_id` | Optional — continue an existing conversation |
| `message` | The user's query |
| `department_id` | Optional origin (department page) |

### 21.2 Agent Routing

- The Coordinator classifies intent and routes to the specialist agent (AI_ARCHITECTURE.md §9).
- The response envelope includes the active agent, handoff metadata, and citations.

### 21.3 AI Response

- Returns the grounded answer, the active agent, and citation list.
- Streaming (future) via `text/event-stream`; the envelope contract stays identical for completed responses.

### 21.4 Citation Response

- Citations are returned with the AI response and retrievable per message via `/api/v1/ai/sources/{message_id}`.
- Each citation carries title, url/path, category, snippet, and relevance score (DATABASE_DESIGN.md §22).

### 21.5 Feedback Submission

- Accepts rating (1–5 / thumbs), optional comment, and optional flag type.
- Linked to the message and conversation; triaged per DATABASE_DESIGN.md §23.

---

## 22. Conversation APIs

Conversation management endpoints (DATABASE_DESIGN.md §15).

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/conversations` | List own conversations (paginated, sorted by last activity) |
| `GET` | `/api/v1/conversations/{id}` | Conversation details (title, summary, status, active agent, message count) |
| `PATCH` | `/api/v1/conversations/{id}` | Rename / update conversation metadata |
| `DELETE` | `/api/v1/conversations/{id}` | Soft-delete a conversation |
| `POST` | `/api/v1/conversations/{id}/archive` | Archive an inactive conversation |
| `POST` | `/api/v1/conversations/{id}/restore` | Restore an archived conversation |

**Lifecycle:** create → active → archived → restore/delete (ui-ux-design.md §13.2; DATABASE_DESIGN.md §35). All routes owner-scoped.

---

## 23. Knowledge Base APIs

Read-side knowledge endpoints (DATABASE_DESIGN.md §21; AI_ARCHITECTURE.md §36).

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/knowledge/search` | Search the knowledge base (query → retrieval) and return relevant chunks with sources |
| `GET` | `/api/v1/knowledge/documents` | List indexed documents (metadata, category, status) |
| `GET` | `/api/v1/knowledge/documents/{document_id}` | Fetch document metadata and source details |
| `GET` | `/api/v1/knowledge/documents/{document_id}/sources` | Retrieve chunks/sources of a document |

### 23.1 Future Admin Upload APIs

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/api/v1/admin/knowledge/documents` | Upload and validate a document (Section 35, 36) |
| `PATCH` | `/api/v1/admin/knowledge/documents/{id}` | Update metadata / category |
| `POST` | `/api/v1/admin/knowledge/documents/{id}/reindex` | Trigger re-ingestion / re-embedding |
| `DELETE` | `/api/v1/admin/knowledge/documents/{id}` | Archive a document |

**Responsibility:** retrieval is public (to authenticated users) but ingestion is admin-only; the vector store is a cache of the knowledge base (AI_ARCHITECTURE.md §36.7).

---

## 24. Health Check APIs

Operational endpoints (no auth; used by orchestration and monitoring).

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/health/live` | Liveness — process is alive (always returns `200` while running) |
| `GET` | `/health/ready` | Readiness — dependencies reachable (database, vector store, AI gateway) |
| `GET` | `/health` | Combined health summary |
| `GET` | `/health/version` | Version information (service, API version, model, build) |

**Contract:** ready returns `200` only when DB, FAISS, and the AI gateway are reachable; `503` otherwise (BACKEND_ARCHITECTURE.md §27). Version endpoint exposes non-sensitive build/model metadata.

---

## 25. Admin APIs (Future)

Placeholders — documented for the admin panel roadmap (ui-ux-design.md §19); admin role required.

| Domain | Endpoints (future) | Purpose |
| ------ | ------------------ | ------- |
| **Students** | `GET/PATCH /api/v1/admin/students`, `GET /api/v1/admin/students/{id}` | Account management, status, profile |
| **Departments** | `GET/POST/PATCH /api/v1/admin/departments`, `GET/DELETE /{id}` | Department CRUD, agent mapping, routing configuration |
| **Knowledge Base** | `GET/POST/PATCH/DELETE /api/v1/admin/knowledge/*`, `POST .../reindex` | Document ingestion, validation, re-indexing, archiving (Section 23.1) |
| **AI Agents** | `GET /api/v1/admin/agents`, `PATCH /api/v1/admin/agents/{key}` | Agent registry, routing config, monitoring views |
| **Requests** | `GET /api/v1/admin/requests`, `PATCH /api/v1/admin/requests/{id}`, `POST .../{id}/{action}` | Cross-student request management, assignment, status transitions |
| **Analytics** | `GET /api/v1/admin/analytics` | KPI dashboards (requests, AI usage, satisfaction) |
| **Reports** | `GET /api/v1/admin/reports` | Exportable operational reports |
| **Settings** | `GET/PUT /api/v1/admin/settings` | System-level configuration |

**Enforcement:** admin role required; audit-logged (DATABASE_DESIGN.md §24); pagination/filter/sort per Sections 9–11.

---

## 26. Error Codes

Application error codes are **stable identifiers** clients can branch on (BACKEND_ARCHITECTURE.md §15). Format: `{PREFIX}{3-digit}`.

| Prefix | Domain | Examples |
| ------ | ------ | -------- |
| `AUTH` | Authentication & tokens | `AUTH001` invalid credentials, `AUTH002` expired token, `AUTH003` invalid token, `AUTH004` email not verified, `AUTH005` account locked, `AUTH006` session revoked |
| `USER` | User & profile | `USER001` email taken, `USER002` profile not found, `USER003` password mismatch, `USER004` invalid settings |
| `REQ` | Requests & workflow | `REQ001` invalid status transition, `REQ002` request not found, `REQ003` not owner, `REQ004` conflict/version mismatch |
| `CHAT` | Conversations & messages | `CHAT001` conversation not found, `CHAT002` not owner, `CHAT003` message send conflict, `CHAT004` conversation archived |
| `AI` | AI service | `AI001` LLM unavailable, `AI002` generation timeout, `AI003` retrieval failure, `AI004` no grounded answer, `AI005` AI service unavailable |
| `KB` | Knowledge base | `KB001` document not found, `KB002` invalid file type, `KB003` file too large, `KB004` ingestion failed, `KB005` search failed |
| `SYS` | System / generic | `SYS001` unexpected error, `SYS002` rate limited, `SYS003` service unavailable, `SYS004` maintenance mode |
| `VAL` | Validation | `VAL001` invalid field, `VAL002` missing field, `VAL003` invalid format, `VAL004` invalid enum, `VAL005` invalid UUID |

**Rules:** codes never change meaning; new codes are additive; `details` provides field-level context for `VAL`/`REQ` errors.

---

## 27. HTTP Status Codes

| Code | Use | Notes |
| ---- | --- | ----- |
| `200` | Success (GET, PATCH, action) | Standard envelope |
| `201` | Created (POST) | `Location` header may indicate the resource |
| `204` | No content (DELETE) | Or `200` with deleted resource per endpoint |
| `400` | Malformed request | Client error outside validation |
| `401` | Unauthenticated | Missing/invalid/expired token (`AUTH*`) |
| `403` | Forbidden | Authenticated but not permitted |
| `404` | Not found | Unknown resource or valid UUID without a record |
| `409` | Conflict | Version mismatch, duplicate, invalid state transition |
| `422` | Validation error | Pydantic field-level `details` |
| `429` | Rate limited | `Retry-After` header set |
| `500` | Internal server error | Generic message, full detail logged |
| `503` | Service unavailable | AI/DB dependency down; maintenance |

**Rules:** codes follow the error-category mapping in BACKEND_ARCHITECTURE.md §15.2; `5xx` never leaks stack traces.

---

## 28. Security Rules

| # | Rule | Detail |
| - | ---- | ------ |
| 1 | **HTTPS only** | TLS everywhere except local dev; HSTS in production |
| 2 | **JWT security** | Short-lived access tokens; hashed refresh tokens; rotation + replay detection (Section 5) |
| 3 | **Input validation** | Pydantic v2 at every boundary (BACKEND_ARCHITECTURE.md §14) |
| 4 | **Output sanitization** | Escaped/sanitized responses; no unsafe HTML; markdown rendered safely client-side (ui-ux-design.md §13.2) |
| 5 | **CORS** | Explicit allow-list of frontend origins only (Section 7.5 of BACKEND_ARCHITECTURE.md) |
| 6 | **Secure headers** | CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` set by middleware |
| 7 | **CSRF considerations** | JWT bearer tokens are header-based (not cookie-authenticated), so CSRF risk is minimized; same-site cookie policy if cookies are later used for refresh |
| 8 | **SQL injection prevention** | ORM/parameterized queries only — never string-built SQL (DATABASE_DESIGN.md §30) |
| 9 | **XSS prevention** | Escape output; never render user content as HTML; sanitize markdown (ui-ux-design.md §33) |
| 10 | **Secrets** | JWT/DB/AI keys from environment only; never logged or returned (PROJECT_RULES.md) |
| 11 | **PII protection** | Never logged, never returned beyond owner scope (Section 37 of AI_ARCHITECTURE.md) |
| 12 | **Rate limiting** | Per-endpoint-class limits (Section 13) |
| 13 | **Audit** | Privileged and sensitive actions logged to `audit_logs` (DATABASE_DESIGN.md §24) |

---

## 29. API Naming Convention

| Item | Convention | Examples |
| ---- | ---------- | -------- |
| Endpoints | `kebab-case`, plural nouns | `/api/v1/requests`, `/api/v1/request-timeline` |
| Resources | Plural nouns; member via `{id}` | `conversations`, `conversations/{id}` |
| HTTP methods | Semantic (GET/POST/PUT/PATCH/DELETE) | Section 2.2 |
| Query parameters | `snake_case` | `status`, `department_id`, `created_from` |
| JSON fields | `snake_case` | `request_no`, `last_message_at`, `is_active` |
| Enum values | `snake_case` | `in_review`, `high`, `admission` |
| Error codes | `PREFIX###` | `AUTH002`, `REQ001` |
| Action sub-resources | Lowercase verb | `/submit`, `/archive`, `/restore` |

**Rule:** naming is consistent across endpoints, schemas, and the database (DATABASE_DESIGN.md §3).

---

## 30. OpenAPI Documentation Rules

| Standard | Detail |
| -------- | ------ |
| Auto-generation | OpenAPI generated from the FastAPI application; served via Swagger UI and ReDoc |
| Tags | Every endpoint grouped by domain tag (auth, users, students, requests, notifications, conversations, ai, knowledge, health, admin) |
| Descriptions | Every endpoint has a summary + purpose; parameters and schemas documented |
| Examples | Request/response examples included per endpoint (Sections 31–32) |
| Response documentation | Every endpoint documents all possible status codes (Section 27) and error codes (Section 26) |
| Auth docs | Bearer auth documented globally; protected endpoints flagged |
| Environment | Docs enabled in development/testing; gated or disabled in production (Section 7.5 of BACKEND_ARCHITECTURE.md) |

---

## 31. Example JSON Requests

Documentation examples of common request payloads (field names follow Section 29).

### 31.1 Register

```json
{
  "full_name": "Ayesha Khan",
  "email": "ayesha.khan@example.edu.pk",
  "password": "secure-pass-123",
  "enrollment_no": "SMIU-2024-0147",
  "department_id": "d97f2c6e-4a3b-4c1d-9e8f-1a2b3c4d5e6f",
  "program_name": "BS Software Engineering"
}
```

### 31.2 Login

```json
{
  "email": "ayesha.khan@example.edu.pk",
  "password": "secure-pass-123"
}
```

### 31.3 Refresh Token

```json
{
  "refresh_token": "<refresh-token>"
}
```

### 31.4 Create Request

```json
{
  "request_type": "admission",
  "department_id": "d97f2c6e-4a3b-4c1d-9e8f-1a2b3c4d5e6f",
  "priority": "high",
  "title": "Verify merit list status for BSSE",
  "description": "I applied for admission but my name is not on the merit list.",
  "source": "chat",
  "conversation_id": "b3a1f0e2-9d84-4c7a-8f2b-6e5d4c3b2a10"
}
```

### 31.5 Send Message (Ask AI)

```json
{
  "message": "What documents are required for BSSE admission?"
}
```

Or continuing a conversation:

```json
{
  "conversation_id": "b3a1f0e2-9d84-4c7a-8f2b-6e5d4c3b2a10",
  "message": "What about the merit list dates?"
}
```

### 31.6 Submit Feedback

```json
{
  "message_id": "9f8e7d6c-5b4a-4a3d-9c2b-1a2b3c4d5e6f",
  "feedback_type": "rating",
  "rating": 5,
  "comment": "Very clear answer."
}
```

### 31.7 Update Profile

```json
{
  "full_name": "Ayesha R. Khan",
  "phone": "+92-300-1234567"
}
```

---

## 32. Example JSON Responses

### 32.1 Success

```json
{
  "success": true,
  "data": {
    "id": "e6b5c4d3-2a1f-4e9d-8c7b-6a5f4e3d2c1b",
    "full_name": "Ayesha Khan",
    "email": "ayesha.khan@example.edu.pk",
    "role": "student",
    "status": "active"
  },
  "meta": {
    "request_id": "e2f7a1c4-8b3d-4f6a-9c1e-5d4b3a2c1f0e",
    "timestamp": "2026-08-01T09:15:00Z"
  }
}
```

### 32.2 Validation Error

```json
{
  "success": false,
  "error": {
    "code": "VAL002",
    "message": "Request validation failed",
    "details": [
      { "field": "email", "reason": "must be a valid email address" },
      { "field": "password", "reason": "must be at least 8 characters" }
    ]
  },
  "meta": {
    "request_id": "e2f7a1c4-8b3d-4f6a-9c1e-5d4b3a2c1f0e",
    "timestamp": "2026-08-01T09:16:00Z"
  }
}
```

### 32.3 Authentication Error

```json
{
  "success": false,
  "error": {
    "code": "AUTH002",
    "message": "Access token has expired",
    "details": null
  },
  "meta": {
    "request_id": "e2f7a1c4-8b3d-4f6a-9c1e-5d4b3a2c1f0e",
    "timestamp": "2026-08-01T09:17:00Z"
  }
}
```

### 32.4 AI Response

```json
{
  "success": true,
  "data": {
    "conversation_id": "b3a1f0e2-9d84-4c7a-8f2b-6e5d4c3b2a10",
    "message_id": "9f8e7d6c-5b4a-4a3d-9c2b-1a2b3c4d5e6f",
    "agent": "admission",
    "content": "For BSSE admission you need: 1) Matric and Intermediate certificates, 2) CNIC or B-Form, 3) two passport-size photographs. Next step: submit the online application before the deadline.",
    "status": "completed",
    "citations": [
      {
        "source_title": "BSSE Admission Guide 2026",
        "source_url": "/knowledge/admission/bscs-admission-guide-2026.pdf",
        "category": "admission",
        "relevance_score": 0.93
      }
    ],
    "handoff": { "routed_to": "admission" }
  },
  "meta": {
    "request_id": "e2f7a1c4-8b3d-4f6a-9c1e-5d4b3a2c1f0e",
    "timestamp": "2026-08-01T09:18:00Z"
  }
}
```

### 32.5 Pagination

```json
{
  "success": true,
  "data": [
    { "id": "c1", "title": "Request A", "status": "in_review" },
    { "id": "c2", "title": "Request B", "status": "submitted" }
  ],
  "meta": {
    "request_id": "e2f7a1c4-8b3d-4f6a-9c1e-5d4b3a2c1f0e",
    "timestamp": "2026-08-01T09:19:00Z",
    "pagination": {
      "page": 2,
      "limit": 20,
      "offset": 20,
      "total": 45,
      "total_pages": 3,
      "next_page": 3,
      "prev_page": 1
    }
  }
}
```

---

## 33. API Lifecycle Management

### 33.1 API Design Process

1. Requirement → resource/endpoint design → schema contract (Pydantic v2) → OpenAPI review → implementation → tests (Section 38) → documentation (Section 30).

### 33.2 API Release Process

- Additive changes ship under the current version with the standard CI gate (lint, type-check, tests, OpenAPI validation).
- New endpoints are documented and tested before merge.

### 33.3 API Deprecation Policy

| Phase | Action |
| ----- | ------ |
| Notice | `Deprecation` header + documented warning |
| Grace period | Endpoints remain functional for a defined window |
| Sunset | Removal after the grace period per the sunset strategy |

### 33.4 Backward Compatibility

- Additive: new fields, endpoints, and optional parameters — no client impact.
- Compatible change rule: existing fields never change meaning or type in the same version.

### 33.5 Breaking Changes Policy

| Change | Policy |
| ------ | ------ |
| Field removal/retype | Requires a new version (`/api/v2`) |
| Behavior change | Requires deprecation + version where observable |
| Endpoint removal | Deprecation → grace period → sunset |
| Exception | Security-critical changes may be immediate with notice + audit |

### 33.6 Sunset Strategy

- Announce, deprecate, co-serve with the new version, then remove within the documented window.
- Every sunset is logged and communicated to the frontend team before execution.

---

## 34. Idempotency Rules

### 34.1 Method Behavior

| Method | Idempotent | Duplicate handling |
| ------ | ---------- | ------------------ |
| `GET` | Yes | Repeatable; no side effects |
| `PUT` | Yes | Full replace — same result on repeat |
| `PATCH` | Best-effort | Guarded by `version` (optimistic lock, DATABASE_DESIGN.md §4.4) |
| `DELETE` | Yes | Second delete returns `200`/`204` or stable `404` |
| `POST` | No | Made idempotent via `Idempotency-Key` for state-changing operations |

### 34.2 Duplicate Request Handling

| Operation | Idempotency mechanism |
| --------- | --------------------- |
| Create request | `Idempotency-Key` header — repeated create returns the same resource |
| Send message | `Idempotency-Key` header — duplicate send produces one message |
| Ask AI | `Idempotency-Key` header — duplicate ask returns the same completed response or in-flight marker |
| Feedback | Keyed by `message_id` — one feedback per type per message |
| Login | Rate-limited; repeated attempts are safe (no resource duplication) |

### 34.3 Retry Safety

- Idempotency keys are stored with the operation; replays within a TTL return the original result (no side effects).
- Expired keys create a new operation — clients must treat the response as authoritative.
- Conflict responses (`409`) require the client to refresh state and retry (Section 27).

---

## 35. File Upload APIs

### 35.1 Supported File Types

| Category | Types |
| -------- | ----- |
| Documents | `pdf`, `doc`, `docx`, `md`, `txt` |
| Images | `png`, `jpg`, `jpeg` |
| Upload scope | Request attachments, profile/identity documents, knowledge ingestion (admin) |

### 35.2 Maximum File Size

| Upload scope | Limit |
| ------------ | ----- |
| Attachments / documents | Configurable cap (e.g., 10 MB) |
| Knowledge ingestion (admin) | Higher cap (e.g., 50 MB) — bounded |
| Images | Tighter cap + dimension checks |

### 35.3 Upload Flow

1. Client uploads via `multipart/form-data` to the target endpoint.
2. Server validates MIME/extension, size, and content (Section 35.4).
3. File stored with a UUID-based safe filename; metadata row created (`documents`, DATABASE_DESIGN.md §20).
4. Response returns the document id, storage path reference, and processing status.

### 35.4 Validation Rules

| Rule | Detail |
| ---- | ------ |
| MIME whitelist | Extension + declared content-type match |
| Size bound | Per-scope limits (Section 35.2) |
| Content check | Non-empty, readable; image dimensions where applicable |
| Checksum | SHA-256 computed and stored (DATABASE_DESIGN.md §20) |
| No executables | Scripts/executables rejected at the boundary |

### 35.5 Virus Scan Strategy

- Files are scanned before use; infected files are rejected and logged (admin-scoped escalation).
- Scanning runs as a background task so uploads are non-blocking.

### 35.6 Storage Strategy

- Bytes live on a dedicated storage path (never a code path); only metadata in the database (Section 18 of BACKEND_ARCHITECTURE.md).
- Storage is behind a repository/service interface so cloud storage can replace local storage without API changes (Section 35.7 of BACKEND_ARCHITECTURE.md).

### 35.7 Error Handling

- Validation failures → `422`/`400` with `KB`/`VAL`-scoped codes and field detail.
- Storage failures → `500`/`503` logged with correlation id; client retries with the same idempotency key.

---

## 36. API Performance Standards

### 36.1 Response Time Targets

| Endpoint class | Target (p95) |
| -------------- | ------------ |
| Read/list endpoints | Fast, sub-second |
| Write endpoints | Sub-second |
| AI endpoints | Bounded by model latency; TTFT optimized (AI_ARCHITECTURE.md §31) |
| Health checks | Sub-second |

### 36.2 Timeout Policy

- General requests: bounded server-side timeout.
- AI requests: bounded per-call timeout with a friendly "taking too long" state (ui-ux-design.md §36).
- Long operations (uploads, re-index) run as background jobs — never synchronous.

### 36.3 Compression

- `gzip`/`br` compression on JSON responses where beneficial.
- Response size reductions applied without weakening the envelope contract.

### 36.4 Caching Headers

| Resource | Policy |
| -------- | ------ |
| Static/public data | `Cache-Control` with short TTL (e.g., departments) |
| User-scoped data | Private, no-store where appropriate |
| AI responses | Cacheable only when identical + safe (idempotency) |
| Version/health | Short TTL |

### 36.5 Connection Reuse

- HTTP/2 + keep-alive; pooled DB connections (DATABASE_DESIGN.md §31).
- Client and server reuse connections to reduce latency.

### 36.6 Payload Optimization

- Field selection (`?fields=`) where needed (future).
- Collections never return full nested graphs; links reference sub-resources.
- Pagination default keeps payloads bounded (Section 9).

### 36.7 Pagination Performance

- Keyset pagination on indexed sort keys for large collections (DATABASE_DESIGN.md §31).
- Counts computed efficiently (or estimated) to avoid scans on hot endpoints.

---

## 37. API Monitoring & Logging

| Category | What is captured |
| -------- | ---------------- |
| **Request logging** | Method, path, status, duration, user id (when available) |
| **Response logging** | Response size, status, latency bucket |
| **Error logging** | Full exception detail, error code, retry/fallback events |
| **Audit logging** | Privileged/sensitive actions → `audit_logs` (DATABASE_DESIGN.md §24) |
| **Correlation IDs** | `X-Correlation-Id` propagated across services (backend → AI → DB) |
| **Trace IDs** | Distributed tracing across FastAPI, AI service, and LLM calls |
| **Performance metrics** | Latency percentiles, token usage, error rate, availability (AI_ARCHITECTURE.md §38) |

**Rules:**

- Never log secrets, tokens, passwords, or raw PII (PROJECT_RULES.md).
- Structured, level-based logs with correlation ids.
- Metrics feed the monitoring pipeline (Section 31 of AI_ARCHITECTURE.md) and the evaluation framework.

---

## 38. API Testing Strategy

| Level | Scope |
| ----- | ----- |
| **Unit testing** | Isolated service/schema logic, mocked boundaries |
| **Integration testing** | Routes + services + database + AI facade together (test DB, mock LLM) |
| **Contract testing** | Request/response shapes pinned against the OpenAPI spec |
| **API validation** | Status codes, error envelopes, pagination/filter/sort behavior verified per endpoint |
| **Swagger verification** | Generated OpenAPI is valid and matches implemented behavior |
| **Postman collection strategy** | Versioned collection mirrors the OpenAPI spec; environment-based; used for manual + smoke testing and CI checks |
| **Regression testing** | Automated suite runs on every change; endpoint behavior must not regress |

**Rules:** tests are part of the Definition of Done (BACKEND_ARCHITECTURE.md §26); tests never hit the real production database; external LLM calls are mocked or gated in CI.

---

## 39. Future API Expansion

| Capability | Phase | Notes |
| ---------- | ----- | ----- |
| **WebSockets** | Future | Real-time notifications and live agent status |
| **Server-Sent Events (SSE)** | Future | Streaming AI responses (`text/event-stream`) |
| **Streaming AI responses** | Future | Token streaming with the same completed-response envelope (AI_ARCHITECTURE.md §18) |
| **Mobile APIs** | Future | Same versioned REST surface; no separate mobile API |
| **GraphQL (future consideration)** | Future | Considered only behind the REST contract for complex read aggregation; not planned |
| **External university integrations** | Future | ERP/LMS integration endpoints; webhook event delivery (outbox pattern, DATABASE_DESIGN.md §33) |

**Expansion rule:** future capabilities extend the existing contract — additive, versioned, and backward compatible (Section 33).

---

## Important

This document is the **permanent API specification** and the **single source of truth for all backend endpoints**.

It must be read together with:

- **PROJECT_RULES.md** — master rules (API standards, naming, security).
- **docs/architecture/BACKEND_ARCHITECTURE.md** — layered architecture, DI, error/validation contracts.
- **docs/architecture/DATABASE_DESIGN.md** — persistence, ownership, retention, and audit tables.
- **docs/architecture/AI_ARCHITECTURE.md** — agent routing, RAG, citations, and AI boundaries.
- **docs/architecture/ui-ux-design.md** — chat states, status models, notification priorities.

All API work — routers, schemas, services, and endpoint tests — must be derived from this document. Any implementation that deviates from this specification must be corrected before it is accepted.

**This document is documentation only.** It contains no implementation code. Implementation is derived from these standards, following the project's Development Rules and Definition of Done.

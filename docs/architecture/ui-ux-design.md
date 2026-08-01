# UI/UX Architecture Document

**Agentic AI-Based University Workflow Automation System**
Multi-Agent Student Support Platform — developed for **Sindh Madressatul Islam University (SMIU)**

> Version: 2.1 · Status: Approved Architecture · Last Updated: July 2026 · Owner: Final Year Project Team
> Scope: Single source of truth for every frontend page, component, layout, interaction, and design decision.
> Sufficiently detailed that the entire frontend can be generated without additional UI instructions. This is a research-based Final Year Project.

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Brand Identity](#2-brand-identity)
3. [Typography](#3-typography)
4. [Spacing System](#4-spacing-system)
5. [Border Radius](#5-border-radius)
6. [Shadow System](#6-shadow-system)
7. [Layout Guidelines](#7-layout-guidelines)
8. [Responsive Breakpoints](#8-responsive-breakpoints)
9. [Navigation System](#9-navigation-system)
10. [UI Components](#10-ui-components)
11. [Forms](#11-forms)
12. [Dashboard Design](#12-dashboard-design)
13. [AI Chat Interface](#13-ai-chat-interface)
14. [AI Response Formatting Rules](#14-ai-response-formatting-rules)
15. [Landing Page](#15-landing-page)
16. [Student Portal Pages](#16-student-portal-pages)
17. [Request Workflow Status](#17-request-workflow-status)
18. [Notification Priority](#18-notification-priority)
19. [Future Admin Panel](#19-future-admin-panel)
20. [Icons](#20-icons)
21. [Animations](#21-animations)
22. [Accessibility](#22-accessibility)
23. [Dark Mode](#23-dark-mode)
24. [Design Tokens](#24-design-tokens)
25. [Component Reusability Rules](#25-component-reusability-rules)
26. [UX Guidelines](#26-ux-guidelines)
27. [File & Component Organization](#27-file--component-organization)
28. [UI Development Rules](#28-ui-development-rules)
29. [Definition of Done (UI)](#29-definition-of-done-ui)
30. [Important](#30-important)
31. [AI UX Principles](#31-ai-ux-principles)
32. [Performance Budget](#32-performance-budget)
33. [Security UI Rules](#33-security-ui-rules)
34. [Empty States](#34-empty-states)
35. [Error Pages](#35-error-pages)
36. [AI Chat States](#36-ai-chat-states)
37. [Mobile UX Guidelines](#37-mobile-ux-guidelines)
38. [Component Naming Convention](#38-component-naming-convention)
39. [Next.js App Router File Convention](#39-nextjs-app-router-file-convention)
40. [Folder Naming Convention](#40-folder-naming-convention)
41. [UI Testing Checklist](#41-ui-testing-checklist)
42. [Design Source Policy](#42-design-source-policy)
43. [AI Generated UI Rules](#43-ai-generated-ui-rules)

---

## 1. Design Philosophy

| # | Principle | Meaning |
| - | --------- | ------- |
| 1 | **Modern University Portal** | A contemporary, trustworthy product feel — like ChatGPT, Linear, or Notion — tailored for an academic institution. |
| 2 | **Professional Appearance** | Polished surfaces, precise alignment, no visual noise. The platform must look dependable. |
| 3 | **Clean Interface** | Quiet surfaces with one or two loud moments; content first, chrome second. |
| 4 | **Minimal Design** | Whitespace-driven. Every element must earn its place. |
| 5 | **User-Centered Experience** | Design for students first, admins second. Small tasks must take the fewest clicks. |
| 6 | **Accessibility-First** | WCAG AA from the first component, not retrofitted later. |
| 7 | **Mobile-First** | Design at 360px and scale up; every layout works on a phone. |
| 8 | **Scalable Design System** | Token-driven, composable, consistent across all pages and future features. |
| 9 | **Consistency Across All Pages** | Same patterns, spacing, and components everywhere. No bespoke redesigns per page. |
| 10 | **Research-Grade Professional UI** | The interface itself is part of the FYP research contribution — it must demonstrate production quality. |

---

## 2. Brand Identity

Implementation note: colors map to Tailwind theme extensions **and** shadcn/ui CSS variables. Dark mode is a pure variable swap — no component changes.

### Primary

| Token | Hex | Usage |
| ----- | --- | ----- |
| `primary` | `#2563EB` | Primary buttons, active nav, links, focus rings, selected states |
| `primary-hover` | `#1D4ED8` | Hover / active press on primary surfaces |
| `primary-active` | `#1E40AF` | Pressed / focused states of primary surfaces |
| `primary-soft` | `#EFF6FF` | Soft fills (selected chips, info banners, table row hover) |

### Secondary

| Token | Hex | Usage |
| ----- | --- | ----- |
| `secondary` | `#0F172A` | Page headings, dark surfaces, footer, text emphasis |

### Accent

| Token | Hex | Usage |
| ----- | --- | ----- |
| `accent` | `#06B6D4` | Info highlights, agent badges, gradient end-stop |

### Semantic Colors

| Token | Hex | Usage |
| ----- | --- | ----- |
| `success` | `#22C55E` | Resolved, approved, online status |
| `warning` | `#F59E0B` | Pending, in-review, warnings |
| `danger` | `#EF4444` | Errors, rejected, destructive actions |
| `information` | `#0EA5E9` | Informational messages, new features |

### Surfaces & Borders

| Token | Hex | Usage |
| ----- | --- | ----- |
| `background` | `#F8FAFC` | App canvas (slate-50) |
| `surface` | `#FFFFFF` | Cards, dialogs, sheets, dropdowns |
| `muted` | `#F1F5F9` | Input fills, skeleton bases, muted surfaces |
| `border` | `#E2E8F0` | Borders and dividers |

### Text

| Token | Hex | Usage |
| ----- | --- | ----- |
| `text-primary` | `#0F172A` | Body text |
| `text-secondary` | `#475569` | Supporting text, table meta |
| `text-muted` | `#94A3B8` | Placeholders, disabled, timestamps |

### Hover / Focus / Disabled

| Token | Hex | Usage |
| ----- | --- | ----- |
| `hover-primary` | `#1D4ED8` | Primary button hover |
| `hover-surface` | `#F1F5F9` | Row / card hover tint |
| `focus-ring` | `#2563EB` | 2px focus ring, 4px offset |
| `disabled-bg` | `#E2E8F0` | Disabled control fill |
| `disabled-text` | `#94A3B8` | Disabled control text |

### Gradients

- `brand-gradient`: `linear-gradient(135deg, #2563EB 0%, #06B6D4 100%)` — CTAs, progress, active markers.
- `hero-mesh`: radial color blobs (blue 12%, cyan 10%, white) over a faint grid pattern.
- `text-gradient`: `bg-clip-text` on the hero headline only (blue → cyan).
- `glass`: `rgba(255,255,255,0.7)` + `backdrop-blur(16px)` + `1px rgba(255,255,255,0.5)` border.

---

## 3. Typography

### Fonts

- **Primary font:** Inter.
- **Fallbacks:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`.
- Headings: Inter 600–800. Body: Inter 400. Stats/analytics: tabular numbers (`font-variant-numeric: tabular-nums`).

### Type Scale

| Style | Size / Line-height | Weight | Used for |
| ----- | ------------------ | ------ | -------- |
| Display | 48px / 56px | 700–800 | Hero headline |
| H1 | 36px / 44px | 700 | Page titles |
| H2 | 30px / 38px | 700 | Section titles |
| H3 | 24px / 32px | 600 | Sub-sections, card titles |
| H4 | 20px / 28px | 600 | Card headings, page subtitles |
| Paragraph | 16px / 26px | 400 | Default reading text |
| Body | 14px / 22px | 400 | Dense UI, tables, forms |
| Small | 13px / 20px | 400–500 | Meta, table cells, captions |
| Caption | 12px / 16px | 500 | Labels, badges, timestamps |

### Special Text

| Text | Size | Weight | Spec |
| ---- | ---- | ------ | ---- |
| Button text | 14px | 600 | Same size across all button variants |
| Navigation | 14px | 500 | Navbar links and sidebar items |
| Uppercase labels | 11px | 600 | Overlines, section eyebrows (`tracking-widest`) |

### Letter Spacing

| Use | Tracking |
| --- | -------- |
| Headings | `-0.02em` |
| Body / paragraph | `0` |
| Small / caption | `0.01em` |
| Uppercase labels | `0.05em` |

---

## 4. Spacing System

**8-point base scale**, with 4px micro-adjustments permitted for fine alignment.

| Token | Value | Used for |
| ----- | ----- | -------- |
| `space-0.5` | 4px | Micro adjustments, icon gaps |
| `space-1` | 8px | Tight gaps, icon–label spacing |
| `space-2` | 16px | Standard component gap, card inner padding (compact) |
| `space-3` | 24px | Card padding (default) |
| `space-4` | 32px | Section-internal spacing, card gap |
| `space-5` | 48px | Between major blocks inside a page |
| `space-6` | 64px | Section separation (mobile `py-16`) |
| `space-7` | 96px | Section separation (desktop `py-24`) |

| Rule | Value |
| ---- | ----- |
| Margin — public page | `px-4` mobile, `px-6` desktop |
| Padding — card | 24px (default), 20px (compact) |
| Gap — card grid | 16px between cards, 32px between sections |
| Grid gap — bento / dashboards | 16–24px |
| Container width — public | 1200px max |
| Container width — app | 1280px max with 280px sidebar |
| Section spacing | `py-24` desktop / `py-16` mobile |

---

## 5. Border Radius

| Token | Value | Component |
| ----- | ----- | --------- |
| `sm` | 8px | Inputs, textareas, selects, chips, table cells |
| `md` | 12px | Buttons, badges, small cards, table containers |
| `lg` | 16px | Cards, dialogs, dropdowns, drawers, alerts |
| `xl` | 20px | Hero panels, feature tiles, chat bubbles |
| `full` | 9999px | Avatars, pills, toggles, icon buttons |

---

## 6. Shadow System

| Layer | Shadow | Used for |
| ----- | ------ | -------- |
| `sm` | `0 1px 2px rgba(15,23,42,0.06)` | Subtle separation, table headers |
| `md` | `0 4px 12px rgba(15,23,42,0.08)` | Cards, dropdowns, stat cards |
| `lg` | `0 12px 32px rgba(15,23,42,0.12)` | Dialogs, drawers, floating panels |
| `hover` | `md` + `translateY(-2px)` | Interactive cards, feature tiles |
| `floating` | `0 16px 48px rgba(15,23,42,0.18)` | Floating chat mockups, FABs, hero illustration |
| `glow` | `0 8px 24px rgba(37,99,235,0.25)` | Primary CTAs, active agent |
| `glass` | transparent fill + `backdrop-blur` + hairline border | Navbar, chat input, glass panels |

---

## 7. Layout Guidelines

### 7.1 Public Layout

Sticky glass navbar (transparent over hero → frosted on scroll) + footer. Navbar height **64px**. Shared by all public pages.

### 7.2 Authentication Layout

Centered auth card on a split screen: left brand panel (gradient mesh + glass product mock), right form card. Single column on mobile.

### 7.3 Student Portal Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  Topbar 64px: ☰ breadcrumbs ······ ⌘K search  🔔  (avatar menu)       │
├──────────────┬───────────────────────────────────────────────────────┤
│  Sidebar     │  Content area (scrollable, slate-50, max-width 1280)  │
│  280px       │                                                       │
│  (rail 80px  │  PageHeader: title + subtitle + primary action        │
│   on md)     │  [tabs / filters]                                     │
│              │  [content grid]                                       │
│  nav groups  │                                                       │
│  agent status│                                                       │
│  user card   │                                                       │
└──────────────┴────────────────────────────────────────────────────────┘
```

### 7.4 Dashboard Layout

Same portal shell. Content is a responsive grid: welcome banner (full width), stat cards row (4), then two-column content grid (main list + side panel).

### 7.5 Admin Layout (Future)

Same shell with the admin navigation set. Placeholder only for the FYP.

### 7.6 Sizing Summary

| Element | Value |
| ------- | ----- |
| Navbar / topbar height | 64px |
| Sidebar width (desktop) | 280px |
| Sidebar rail (md) | 80px |
| Content max-width | 1280px |
| Public container | 1200px |
| Footer | multi-column, `secondary` background |
| Responsive container | fluid with `px-4/6`, clamped by max-width |

---

## 8. Responsive Breakpoints

| Name | Width | Behavior |
| ---- | ----- | -------- |
| `sm` Mobile | 640px | Single-column stacks, tables → cards, hamburger menus, bottom-safe tap targets (≥44px) |
| `md` Tablet | 768px | 2-col grids, sidebar → 80px rail, forms 2-col where sensible |
| `lg` Laptop | 1024px | Full sidebar restored, tables remain tabular, 3-col bento |
| `xl` Desktop | 1280px | Public max-width, hero mockup expands, 4-col stat rows |
| `2xl` Large desktop | 1536px | Full content width, dashboards multi-column |

**Responsive rules per layout:**

- **Public:** bento → single column; hero stacks; navbar → hamburger drawer.
- **Auth:** split screen → centered single card.
- **Student portal:** sidebar → rail → off-canvas drawer; tables → stacked cards; chat input grows with viewport.
- **Admin (future):** tables → cards; charts stack vertically.

---

## 9. Navigation System

### 9.1 Sitemap & Route Guards

```
/
├── about                    Public site
├── features
├── how-it-works
├── faq
├── contact
├── login
├── register
│
├── (authenticated — student)
│   ├── /dashboard
│   ├── /dashboard/requests
│   ├── /dashboard/requests/new
│   ├── /dashboard/requests/[id]          Request detail
│   ├── /dashboard/history
│   ├── /dashboard/notifications
│   ├── /dashboard/profile
│   ├── /dashboard/settings
│   ├── /chat
│   └── /chat/[conversationId]
│
└── (authenticated — admin)
    ├── /admin
    ├── /admin/students
    ├── /admin/departments
    ├── /admin/knowledge-base
    ├── /admin/agents
    ├── /admin/requests
    ├── /admin/analytics
    ├── /admin/reports
    └── /admin/settings
```

| Route group | Access | Layout |
| ----------- | ------ | ------ |
| Public `/`, `/about`, `/features`, ... | Anonymous | Public shell (Navbar + Footer) |
| Student `/dashboard`, `/chat` | Authenticated, role=student | App shell (sidebar + topbar) |
| `/chat/*` | Authenticated students (faculty: future) | App shell, chat-focused |
| Admin `/admin/*` | Authenticated, role=admin | App shell, admin nav set |
| `/login`, `/register` | Redirect to `/dashboard` if logged in | Centered auth layout |

Not-found → custom 404. Forbidden → custom 403. Auth redirects preserve `next` param.

### 9.2 Top Navigation (Public)

Links: Home, About, Features, How It Works, FAQ, Contact + Login / "Get Started" buttons. Sticky, glass on scroll.

### 9.3 Sidebar (App)

**Student:** Dashboard, My Requests, New Request, Chat with AI, Conversation History, Notifications, Profile, Settings.
**Admin (future):** Dashboard, Students, Departments, Knowledge Base, AI Agents, Requests, Analytics, Reports, Settings.
Active state = primary-soft pill + primary text + 3px left indicator.

### 9.4 Breadcrumbs

`Home / Dashboard / Requests`; chevron separators; current page = plain text; truncated on mobile.

### 9.5 Mobile Navigation

Hamburger → off-canvas drawer (student/admin) with same sidebar content + user card. Public: simple menu drawer.

### 9.6 Profile Menu

Avatar dropdown: Profile, Settings, Appearance (theme toggle), Sign out.

### 9.7 Notifications

Bell icon with unread dot → popover feed (Requests / AI / System tabs, "Mark all as read", link to full notifications page).

### 9.8 Search

Global command palette (⌘K): navigate pages, requests, conversations, knowledge documents, with keyboard-first results.

---

## 10. UI Components

All components are designed once and reused everywhere. Naming matches `components/ui` (primitives) and `components/{feature}` (composites).

| # | Component | Spec |
| - | --------- | ---- |
| 10.1 | **Buttons** | Variants: primary, secondary, outline, ghost, destructive, accent (gradient). Sizes: sm / md / lg / icon. States: default, hover, active, focus-ring, disabled, loading. Primary CTA uses `glow`. |
| 10.2 | **Cards** | Variants: default, interactive (hover lift), stat (icon tile + label + value + delta), chart, agent. Anatomy: 24px padding, rounded-lg, hairline border, optional header. |
| 10.3 | **Forms** | Field anatomy: label → control → helper → error. Validation inline on blur + submit. See §11. |
| 10.4 | **Inputs** | 8px radius, `muted` fill, border on hover, primary focus ring. Prefix/suffix icons optional. |
| 10.5 | **Textarea** | Same spec as inputs; autosize for chat; 4px min-height, resizable vertically. |
| 10.6 | **Select** | Custom trigger styled like an input + Radix listbox; keyboard searchable. |
| 10.7 | **Checkbox** | Primary accent when checked; 16px target; label on the right. |
| 10.8 | **Radio** | Grouped options; primary dot when selected; 44px tap target. |
| 10.9 | **Switch** | 36×20px track, 16px thumb, primary when on; used for preferences. |
| 10.10 | **Modal** | Centered, backdrop blur, rounded-lg, `lg` shadow, scale-in, focus trap, Esc/backdrop close. |
| 10.11 | **Drawer** | Side sheet (400px) for details/forms; slides in; used in lists and chat. |
| 10.12 | **Dropdown** | Context menu, select, notification popover, command palette. Radix; rounded-lg; smooth scale+fade. |
| 10.13 | **Tooltip** | Small, dark, 2–4 word helper; appears on hover/focus after 300ms. |
| 10.14 | **Badge** | Variants: default, primary, success, warning, danger, outline. Used for status (Pending / In Review / Resolved / Rejected). |
| 10.15 | **Alert** | Inline message with icon; variants info / success / warning / danger; dismissible. |
| 10.16 | **Toast** | Top-right stack; success/error/info/warning; optional action; auto-dismiss 4s (errors persist). |
| 10.17 | **Tabs** | Underline or pill variants; keyboard arrow navigation; used for filters and settings. |
| 10.18 | **Accordion** | Single-open; chevron rotate; used in FAQ and filters. |
| 10.19 | **Avatar** | Circular, `full` radius; initials fallback; sizes sm 24 / md 32 / lg 40 / xl 64. |
| 10.20 | **Table** | Header slate-50, hover tint, sortable headers, row actions menu; under `md` rows become cards. |
| 10.21 | **Pagination** | Prev/next + page numbers; shows range summary; responsive (numbers hide on mobile). |
| 10.22 | **Search Bar** | Input with magnifier icon; variant: inline filter or ⌘K command palette. |
| 10.23 | **Loading Spinner** | Circular, primary, sizes 16/20/24; centered in buttons and panels. |
| 10.24 | **Skeleton Loader** | Shimmer; matches final layout 1:1 (table rows, stat cards, chat bubbles, hero text). |
| 10.25 | **Empty State** | Centered icon in soft disc, title, description, one primary action. Used on every list/dashboard. |
| 10.26 | **Error State** | Inline alert with retry, or full error page (404 / 403 / 500) with home/back actions. |

**Composites:** `Navbar`, `Footer`, `Sidebar` (see §7/§9), `StatCard`, `ChartCard`, `DataTable`, `FilterBar`, `StatusBadge`, `QuickActionGrid`, `WelcomeBanner`, `ConversationItem`, `NotificationItem`, `HistoryGroup`, `SettingsNav`, `AgentCard`, `SyncCard`, `DangerZone`.

---

## 11. Forms

| Rule | Spec |
| ---- | ---- |
| **Label position** | Top-aligned above the control; required fields show `*`; optional fields show `(optional)`. |
| **Validation** | Client (on blur + submit) then server (Pydantic). Never rely on one layer only. |
| **Required fields** | Asterisk + enforced validation; submit disabled until valid where appropriate. |
| **Optional fields** | Explicitly labeled `(optional)`, never assumed. |
| **Error messages** | Inline below control, danger color + alert icon, human-readable ("Enter a valid email"), `role="alert"`. |
| **Success messages** | Green check near field or form-level success banner after submission. |
| **Disabled state** | `muted` fill, `disabled-text`, no hover/focus, cursor not-allowed. |
| **Loading state** | Button shows spinner + keeps width; fields locked while submitting. |
| **Focus** | Visible primary ring on every control. |

---

## 12. Dashboard Design

The student dashboard is the primary authenticated view.

| Element | Spec |
| ------- | ---- |
| **Sidebar** | §9.3 — student nav set with agent-status mini card. |
| **Header / topbar** | Breadcrumbs, ⌘K search, notification bell, profile menu. |
| **Welcome card** | Glass/gradient banner: "Good morning, Ayesha 👋", one-line AI summary of pending items, quick action buttons (New Request, Chat with AI). |
| **Statistics cards (4)** | Active Requests, Pending, Resolved (30d), Unread Notifications — icon tile, label, value, delta. |
| **Quick actions** | New Request, Chat with AI, Ask Department — icon grid, 4–6 items. |
| **Recent activity** | Recent requests table (title, status badge, updated) + recent conversations with "Continue". |
| **Notifications** | Summary card linking to the full notifications page. |
| **Profile summary** | Avatar + name + department + verified badge in sidebar user card. |

---

## 13. AI Chat Interface

ChatGPT-inspired, adapted for the university multi-agent context.

### 13.1 Layout

```
┌────────────────┬─────────────────────────────────────────────────────────┐
│  Sidebar       │  Header: agent avatar ● status · model badge · actions  │
│  300px         ├─────────────────────────────────────────────────────────┤
│  ● New chat    │                                                          │
│  🔍 search     │                  Chat window (scrollable)                │
│  ───────────── │                                                          │
│  History       │      ┌─ user message (right, primary tint) ──────┐      │
│  Today         │      └────────────────────────────────────────────┘      │
│  · item        │      ┌─ agent message (card, avatar, markdown) ────┐     │
│  Yesterday     │      │  [sources/citations]  [feedback thumbs]      │     │
│  · item        │      └──────────────────────────────────────────────┘    │
│  ───────────── │      ◍  typing indicator / streaming text               │
│  User card     │                                                          │
│                ├─────────────────────────────────────────────────────────┤
│  ⚙  Settings   │  Suggested prompts (chips) [on empty state]              │
│                │  ┌───────────────────────────────┐  [attach] [send]      │
│                │  │ Input area (glass, autosize)  │                        │
│                │  └───────────────────────────────┘  quick actions row    │
└────────────────┴─────────────────────────────────────────────────────────┘
```

### 13.2 Chat Bubbles

| Element | Spec |
| ------- | ---- |
| **User message** | Right-aligned, primary tint bubble, rounded-xl, max-width 70%. |
| **AI message** | Left card with agent avatar, white surface, markdown rendered, rounded-xl. |
| **Typing indicator** | Three bouncing dots + agent avatar pulse while "thinking". |
| **Suggested questions** | 3–4 chips on empty state, category-aware (Admissions, Fees, Exams, General). Click = prefill, editable, then send. |
| **Markdown rendering** | Headings, bold, italic, lists, links rendered safely; no raw HTML. |
| **Code blocks** | Monospace, dark block with copy button, language label. |
| **Tables** | Rendered with header row, zebra rows, horizontal scroll. |
| **Links** | Primary color, underline on hover, open in new tab, safe target. |
| **Sources** | Collapsible citations from RAG under AI messages ("Sources: 2") — title + link per source. |
| **Loading animation** | Skeleton chat bubble while the first token is prepared; then streaming. |
| **Error state** | Inline danger alert + Retry chip; the draft message is preserved. |
| **Empty state** | Centered brand mark, "What can I help you with today?", prompt chips. |
| **Conversation history** | Sidebar grouped by Today / Yesterday / This week / Older; resume or delete. |

### 13.3 Message States

Sending → streaming (token reveal + caret) → sent ✓ → error (retry) / agent-switch notice. Preserved across navigation via conversation history.

### 13.4 Agent Handoff

Divider chip appears when the Coordinator routes to a specialist: "Routed to Examination Agent →". Header reflects the active agent + status dot.

### 13.5 Input Area & Quick Actions

Glass card, autosizing textarea (Enter send, Shift+Enter newline), Attach, Send / Stop toggle. Quick actions: Convert to Request, Summarize, Copy, Export PDF, Ask Department.

---

## 14. AI Response Formatting Rules

AI responses must always follow these formatting rules to ensure readability, consistency, and a professional user experience.

| Rule | Requirement |
|------|-------------|
| Short paragraphs | Keep responses concise and easy to read. Avoid large text blocks. |
| Bullet points | Use bullet lists whenever presenting multiple items. |
| Numbered steps | Use numbered lists for procedures, workflows, or instructions. |
| Bold highlights | Highlight important information using bold text only when necessary. |
| Tables | Use tables only when comparing structured information or data. |
| Markdown | Preserve proper Markdown formatting for headings, lists, tables, links, and code blocks. |
| Readability | Responses should be well-structured and visually organized. |
| Avoid walls of text | Never generate long, unformatted paragraphs. |

---

## 15. Landing Page

Section-by-section spec for `/` (order matters — narrative arc).

| # | Section | Spec |
| - | ------- | ---- |
| 15.1 | **Hero** | Full-viewport, hero-mesh bg + faint grid, eyebrow badge, Display headline with `text-gradient`, subcopy, dual CTA (Get Started / Talk to the AI). |
| 15.2 | **AI Illustration** | Floating glass chat mockup (user + agent bubbles, handoff chip, streaming caret) with layered shadows and gradient orbs; gentle float animation. |
| 15.3 | **Features** | 6-card bento: AI Assistant, Smart Request Workflow, Multi-Agent Routing, Knowledge Base (RAG), Dashboards & Analytics, Notifications. |
| 15.4 | **AI Agents** | Agent cards — Coordinator, Admission, Examination, FAQ — icon, role, "Ask this agent" link into chat. |
| 15.5 | **Workflow (How It Works)** | 4-step timeline with gradient connector: **Ask → Route → Retrieve → Resolve**. |
| 15.6 | **Benefits** | Two-column: copy + checklist (24/7 availability, faster resolution, centralized knowledge, transparent tracking) + glass illustration. |
| 15.7 | **Statistics** | Band with animated counters: response time, resolution rate, active students, departments served. |
| 15.8 | **FAQ** | Accordion, 6–8 questions; link to full `/faq`. |
| 15.9 | **Testimonials** | Future placeholder — 3-card grid, quote, name, department, 5-star rating. |
| 15.10 | **CTA** | `brand-gradient` panel: "Ready to experience effortless university support?" + Register (primary) / Contact (secondary). |
| 15.11 | **Footer** | Multi-column, dark `secondary` background, newsletter + social + legal. |

### 15.12 Supporting Public Pages

| Page | Purpose / Sections / Flow |
| ---- | ------------------------- |
| **About** `/about` | Purpose: trust. Hero → Mission & vision cards → Platform overview → Statistics band → Team → CTA. Flow: read → register. |
| **Features** `/features` | Purpose: showcase scope. Hero → feature bento grid → persona tabs (Student / Admin) → CTA. |
| **How It Works** `/how-it-works` | Purpose: explain the agent pipeline. Hero → 4-step timeline → agent role cards → architecture diagram → CTA. |
| **FAQ** `/faq` | Purpose: reduce support load. Hero + search → topic chips → accordion groups → support card. |
| **Contact** `/contact` | Purpose: support/feedback. Split layout: form + contact cards (email, office, hours) → success state. |
| **Login** `/login` | Purpose: authenticate + role-route. Split screen: brand panel + auth card (email, password, remember, forgot, SSO future) → role redirect. |
| **Register** `/register` | Purpose: student account. Split screen + form (name, email, password + confirm, department, enrollment ID, terms) → email verification notice. |

---

## 16. Student Portal Pages

All pages share the App Shell (§7.3).

| Page | Purpose / Main Sections / Components / Flow |
| ---- | -------------------------------------------- |
| **Dashboard** `/dashboard` | Command center. Welcome banner → stat cards → recent requests → recent conversations → deadlines (future). Components: `WelcomeBanner`, `StatCard`, `DataTable`, `ConversationItem`, `QuickActionGrid`. Flow: glance stats → open item → new request/chat. |
| **My Requests** `/dashboard/requests` | Manage requests. Filter bar (status chips, search, sort, date) → requests table → pagination. Flow: filter → open → track. |
| **New Request** `/dashboard/requests/new` | Create a request. Stepper (Type → Details → Review) → form card (category, department, priority, title, description, attachments) + AI assist panel → submit → toast. |
| **AI Chat** `/chat` | Full interface per §13. Entry: sidebar, dashboard quick action, request "Contact". |
| **Chat History** `/dashboard/history` | Browse/resume/delete sessions. Search → grouped list (Today / Yesterday / Week / Older) → row menu (Open / Rename / Export / Delete). |
| **Notifications** `/dashboard/notifications` | Activity feed. Tabs (All / Requests / AI / System) → notification list with unread dots and action links → empty state. |
| **Profile** `/dashboard/profile` | Edit personal + academic info. Header card (avatar, name, department, verified badge) → tabs (Personal / Academic / Security) → save → toast. |
| **Settings** `/dashboard/settings` | Preferences. Settings nav: Appearance (Light/Dark/System), Notifications, Privacy, Security (password, sessions), Language → Danger zone. |
| **Admission** `/dashboard/admission` | Admission support. Agent-powered answers, admission requirements, eligibility checklist, required documents, merit queries, process steps, "Ask the Admission Agent" entry into chat. |
| **Examination** `/dashboard/examination` | Exam support. Date sheet, results, admit cards, exam rules, improvement policy, "Ask the Examination Agent" entry into chat. |
| **FAQ** `/dashboard/faq` | Knowledge base FAQ. Searchable accordion grouped by topic, office timings, campus info, contact cards, "Ask the FAQ Agent". |

---

## 17. Request Workflow Status

Every student request must follow a standardized lifecycle.

| Status | Description |
|---------|-------------|
| Draft | Request created but not submitted |
| Submitted | Successfully submitted |
| In Review | Under department review |
| Assigned | Assigned to the responsible department or staff |
| Processing | Work is currently in progress |
| Resolved | Issue successfully resolved |
| Closed | Request completed and archived |
| Rejected | Request declined with reason |

Every request status must always display:

- Status Badge
- Timeline Progress
- Timestamp
- Responsible Department (when available)

---

## 18. Notification Priority

Notifications must follow a consistent priority system to improve user awareness and maintain a predictable experience.

| Priority | Examples | UI Behavior |
|----------|----------|-------------|
| Critical | Examination updates, Admission deadlines | Red badge, immediate notification, highest priority |
| High | Request status changes, important approvals | Orange badge, shown before normal notifications |
| Medium | AI recommendations, reminders | Blue badge, standard notification behavior |
| Low | General announcements, informational updates | Gray badge, lowest priority |

Notification priority determines:

- Badge color
- Sorting order
- Toast appearance
- Notification grouping
- Display priority throughout the application

---

## 19. Future Admin Panel

Placeholders only — not implemented in the current FYP.

| Page | Status |
| ---- | ------ |
| **Dashboard** | Admin KPI overview — future |
| **Students** | Student account management — future |
| **Agents** | Agent monitoring & configuration — future |
| **Knowledge Base** | RAG content curation — future |
| **Logs** | System & agent logs — future |
| **Analytics** | Metrics & drill-down — future |

Design will reuse the same App Shell, tokens, and component library.

---

## 20. Icons

- **Library:** Lucide React.
- **Sizes:** 16 (inline/meta), 20 (buttons/inputs), 24 (navigation/cards).
- **Style:** consistent 2px stroke; filled only for status/star indicators.
- **Usage rules:** icons pair with text in primary actions; never used alone for critical information; hover/tooltip required when icon-only.

---

## 21. Animations

| Type | Duration | Easing | Use |
| ---- | -------- | ------ | --- |
| **Hover** | 150ms | `ease-out` | Button, card lift, link underline |
| **Fade** | 200ms | `ease-out` | Tab content, dropdown open |
| **Slide** | 250ms | `cubic-bezier(0.16,1,0.3,1)` | Drawer, toast, sidebar collapse |
| **Scale** | 200ms | same | Dialog open (`0.96 → 1`), popover |
| **Loading** | continuous | linear | Skeleton shimmer, spinner, typing dots |
| **Page transition** | 400ms | same | Section fade-up with 60ms stagger |
| **Modal animation** | 250ms | same | Backdrop fade + content scale |

Respect `prefers-reduced-motion`: disable stagger/parallax/float, keep opacity-only transitions.

---

## 22. Accessibility

Follow **WCAG AA**.

| Area | Requirement |
| ---- | ----------- |
| **Keyboard navigation** | Full tab order, arrow keys in menus/tabs, Esc closes overlays, focus never trapped (except dialogs/menus where Radix manages it). |
| **ARIA** | Correct roles/labels on all interactive elements; `role="alert"` for errors; `aria-live` for chat streaming and toasts. |
| **Focus states** | Visible 2px primary ring with 4px offset on all focusable elements. |
| **Color contrast** | AA contrast (text on gradients only inside glass panels); semantic colors never sole indicators (paired with text/icons). |
| **Screen readers** | Semantic HTML, one `h1` per page, alt text on all images, label every field. |
| **Reduced motion** | `prefers-reduced-motion` honored; opacity-only transitions. |

---

## 23. Dark Mode

**Future support only** — designed for now, not shipped in Phase 1.

- All colors are semantic CSS variables (shadcn pattern); dark mode = variable swap via `class` strategy, no component changes.
- Default = System; toggle in Settings (Appearance) and auth screens.
- Dark tokens: `background #0B1120`, `surface #111C33`, border `rgba(148,163,184,0.15)`, `primary #3B82F6`, text `#F1F5F9` / `#94A3B8`; gradients desaturated ~15%.

**Future expansion roadmap:** Phase 1 design tokens + shells + public site + auth → Phase 2 student portal + chat → Phase 3 admin + analytics → Phase 4 dark mode + i18n (Urdu) + e2e suite → Phase 5 agent live view + PWA shell.

---

## 24. Design Tokens

Reusable token catalog (also in §2–§6). Implemented as Tailwind theme extensions + shadcn CSS variables.

| Group | Tokens |
| ----- | ------ |
| **Colors** | `primary`, `primary-hover`, `primary-soft`, `secondary`, `accent`, `success`, `warning`, `danger`, `information`, `background`, `surface`, `muted`, `border`, `text-primary`, `text-secondary`, `text-muted` |
| **Spacing** | `space-0.5` 4px → `space-7` 96px (8-pt base) |
| **Radius** | `sm` 8, `md` 12, `lg` 16, `xl` 20, `full` 9999px |
| **Shadow** | `sm`, `md`, `lg`, `hover`, `floating`, `glow`, `glass` |
| **Typography** | Display → Caption scale, Inter, weights 400–800, tracking per §3 |
| **Motion** | 150 / 200 / 250 / 400ms + shared easing `cubic-bezier(0.16,1,0.3,1)` |

---

## 25. Component Reusability Rules

- **Never duplicate components** — search `components/ui` and `components/{feature}` before creating.
- **Reuse existing UI** — build pages from the shared library only.
- **Create shared components** — anything used in 2+ places becomes a shared component.
- **Keep components small** — one purpose, one file, focused props.
- **Single Responsibility Principle** — a component renders; logic lives in hooks/services.

---

## 26. UX Guidelines

| Principle | Rule |
| --------- | ---- |
| **Consistency** | Same components, spacing, and patterns across all pages. |
| **Feedback** | Every action produces visible feedback (toast, state change, animation). |
| **Loading** | Always show a skeleton/spinner; never leave a blank screen. |
| **Errors** | Friendly, actionable, with retry — never raw stack traces. |
| **Navigation** | Breadcrumbs + sidebar active state; never require the browser back button. |
| **Discoverability** | Primary actions visible above the fold; search (⌘K) finds anything. |
| **Efficiency** | Fewest clicks for the most common tasks (New Request, Ask AI). |
| **Simplicity** | One primary action per view; progressive disclosure for detail. |

---

## 27. File & Component Organization

| Folder | Contents |
| ------ | -------- |
| `app/` | Routes per App Router; `(auth)`, `(dashboard)`, `chat` route groups |
| `components/layouts/` | Shells: public navbar/footer, app sidebar/topbar |
| `components/ui/` | shadcn/ui primitives (button, dialog, table, ...) |
| `components/features/` | Feature composites: `chat/`, `dashboard/`, `marketing/`, `forms/` |
| `components/shared/` | Cross-feature shared composites (stat card, status badge, empty state) |
| `hooks/` | Custom React hooks (auth, chat, media queries) |
| `services/` | API client and data-access layer |
| `types/` | Shared TypeScript types/interfaces |
| `assets/` | Static assets: images, fonts, illustrations |

**Implementation mapping:** `app/(auth)` → login/register, `app/(dashboard)` → student portal, `app/chat` → chat interface. Design tokens land in `frontend/styles/globals.css` + `tailwind.config`.

---

## 28. UI Development Rules

Every generated frontend **must**:

- Follow **PROJECT_RULES.md**.
- Follow **this UI/UX documentation**.
- **Never create duplicate components.**
- **Always reuse existing components.**
- Use **shadcn/ui**.
- Use **Tailwind CSS**.
- Use **strict TypeScript**.
- Be **responsive**.
- Be **accessible**.
- Be **production-ready**.

---

## 29. Definition of Done (UI)

A UI feature is complete only when it is:

- **Responsive** — verified at all breakpoints.
- **Accessible** — WCAG AA, keyboard + screen-reader tested.
- **Consistent** — uses design tokens and the shared library.
- **Reusable** — no duplicated markup or styles.
- **Validated** — client + server validation where forms are involved.
- **Loading state** — skeleton/spinner present.
- **Error state** — friendly failure + retry present.
- **Empty state** — meaningful empty view present.
- **Skeleton** — matches final layout.
- **Dark mode ready** — built on variables (future support).
- **Production ready** — typed, documented, and deployable.

---

## 30. Important

This document is the **permanent UI/UX guide** for the project.

It is the **single source of truth for frontend development**. All future UI code — pages, components, layouts, and interactions — must strictly follow this document.

This documentation contains **no implementation code** — it is a specification only. AI and developers must derive all frontend code from these rules and the shared design tokens.

---

## 31. AI UX Principles

| # | Principle | Rule |
| - | --------- | ---- |
| 28.1 | **Streaming responses** | AI responses must stream token-by-token; never deliver a single delayed block. |
| 28.2 | **Loading / thinking state** | Always show a visible loading or thinking indicator while the AI works — never a blank screen. |
| 28.3 | **Retry on failure** | Every AI failure must surface an inline error with a Retry action; the draft message is preserved. |
| 28.4 | **Copy support** | Long responses must support one-click Copy. |
| 28.5 | **Collapsible sources** | RAG sources / citations must be collapsible ("Sources: 2" → expand). |
| 28.6 | **Distinct AI / system messages** | AI and system messages must be visually different from user messages (tint, surface, avatar). |
| 28.7 | **Visible agent handoff** | Agent handoff must always be visible — divider chip: "Routed to Examination Agent →". |
| 28.8 | **Preserved conversation history** | Conversation history must be preserved and resumable across sessions. |
| 28.9 | **Active agent identity** | The active agent must be shown in the chat header (avatar, name, status dot). |
| 28.10 | **Duplicate prevention** | Prevent duplicate submissions while streaming (send disabled / Stop toggle). |

---

## 32. Performance Budget

| Metric | Target | How |
| ------ | ------ | --- |
| Initial JS bundle | `< 250 KB` | Lazy loading, dynamic imports, code splitting |
| LCP | `< 2.5 s` | Image optimization, font optimization, preloaded critical paths |
| CLS | `< 0.1` | Reserved dimensions, skeleton layouts, stable UI |
| INP | Within Core Web Vitals recommendations | Avoid unnecessary re-renders, debounce heavy work |
| TTI | `< 3 s` | Defer non-critical scripts, route-level splits |

**Mandatory techniques:**

| Technique | Requirement |
| --------- | ----------- |
| **Lazy loading** | Required for below-the-fold sections and heavy components |
| **Dynamic imports** | Required for chart libraries, the markdown renderer, and heavy features |
| **Code splitting** | Mandatory per route (App Router file-based) |
| **Image optimization** | Mandatory — Next.js `next/image`, correct formats and sizes |
| **Font optimization** | Required — `next/font` (Inter), `display: swap` |
| **Skeleton loading** | Required on every data view — never blank screens |
| **Re-renders** | Avoid unnecessary re-renders; memoize expensive subtrees |

---

## 33. Security UI Rules

| Rule | Spec |
| ---- | ---- |
| **JWT never in UI** | Tokens must never be displayed, logged, or placed in URLs. |
| **Passwords always masked** | Password fields always `type="password"` with a toggle; never plaintext. |
| **Sensitive data never exposed** | Sensitive data (IDs, tokens, financial details) never exposed in the UI, DOM, or devtools. |
| **Role-based navigation** | Nav items rendered from the user's role only; no hidden-by-CSS permission checks. |
| **Protected routes** | All authenticated routes guarded on server and client; redirect with `next` param. |
| **Session expiration** | Expired sessions handled gracefully — modal / redirect to login, drafts preserved where possible. |
| **Destructive confirmations** | Destructive actions require a confirmation dialog (typed confirmation for critical ones). |
| **Secure file upload UI** | Upload UI: type/size limits, scan notice, progress, failure handling. |
| **Email verification flow** | Verification flow with resend, clear status messages, and expiry handling. |
| **Sanitized content** | User-generated content sanitized before render — no raw HTML, no scripts. |

---

## 34. Empty States

Every empty state follows the pattern: **centered icon in soft disc → title → description → one primary CTA** (§10.25). Dedicated specifications per area:

| Area | Icon | Title | Description | Primary CTA |
| ---- | ---- | ----- | ----------- | ----------- |
| **Dashboard** | `LayoutDashboard` | Welcome to your dashboard | Your requests, AI chats, and deadlines will appear here. | New Request |
| **Requests** | `ClipboardList` | No requests yet | Create your first request and track it in real time. | New Request |
| **Notifications** | `BellOff` | You're all caught up | New activity will appear here as it happens. | Go to Dashboard |
| **Chat** | `MessagesSquare` | What can I help you with? | Ask about admissions, exams, or anything university-related. | Suggested prompt chips |
| **Search** | `Search` | No results found | Try different keywords or check the spelling. | Clear filters / View all |
| **History** | `History` | No conversation history | Your AI conversations will be saved here. | Start new chat |
| **Admission** | `GraduationCap` | No admission data yet | Requirements, eligibility, and documents will appear here. | Ask the Admission Agent |
| **Examination** | `FileText` | No exam information yet | Date sheets, results, and rules will appear here. | Ask the Examination Agent |
| **FAQ** | `HelpCircle` | No questions yet | Browse the knowledge base or ask the FAQ Agent. | Ask the FAQ Agent |

---

## 35. Error Pages

| Page | Illustration | Message | CTA | Recovery flow |
| ---- | ------------ | ------- | --- | ------------- |
| **401 Unauthorized** | Shield-off / lock icon | "You need to sign in to view this page." | Sign in | Redirect to `/login` with `next` param; return to the original page after auth. |
| **403 Forbidden** | Lock / no-entry icon | "You don't have permission to view this page." | Go to Dashboard | Redirect to the user's allowed home (dashboard or admin). |
| **404 Not Found** | Search / broken-link icon | "Page not found." | Back to Home | Breadcrumb / correct URL suggested; log and track broken links. |
| **429 Too Many Requests** | Timer / hourglass icon | "You're moving too fast — please wait a moment." | Try again | Show a retry countdown; respect the rate-limit window; auto-retry when safe. |
| **500 Internal Server Error** | Server / warning icon | "Something went wrong on our side." | Try again / Back to Home | Log error with correlation ID; retry; escalate to support if repeated. |
| **503 Maintenance Mode** | Wrench / construction icon | "We're under maintenance — back shortly." | Refresh / Contact support | Show expected duration; poll a status endpoint; reload when live. |

---

## 36. AI Chat States

Complete lifecycle of a chat message (extends §13.3):

| State | Trigger | UI behavior |
| ----- | ------- | ----------- |
| **Idle** | No activity | Input ready, suggested prompts visible, empty state shown. |
| **Typing** | User composing | Send button enabled; Enter send, Shift+Enter newline; textarea state. |
| **Sending** | Submit pressed | Message renders right-aligned, button switches to spinner, input locked. |
| **Streaming** | Tokens arriving | Token reveal + caret; stop button shown; `aria-live` region; message grows in place. |
| **Thinking** | Before first token | Skeleton chat bubble or three-dot typing indicator with agent avatar pulse. |
| **Routed to Agent** | Coordinator handoff | Divider chip: "Routed to Examination Agent →"; header updates to the active agent. |
| **Waiting** | Specialist agent processing | Keep streaming / thinking indicator; status text like "Examination Agent is working…". |
| **Retry** | Failure after error | Inline danger alert + Retry chip; draft preserved. |
| **Timeout** | No response within limit | Timeout message + Retry; partial response kept if any. |
| **Offline** | Network lost | Offline banner; input disabled or queued; auto-reconnect attempt. |
| **Cancelled** | User stops stream | Stop → stream ends at the last token; partial response retained with "Stopped". |
| **Rate Limited** | 429 from the AI provider | Friendly rate-limit notice with countdown; input enabled after the window. |
| **Completed** | Response finished | Sent ✓; action row appears (Copy, Summarize, Convert to Request, Export, feedback). |

---

## 37. Mobile UX Guidelines

| Pattern | Spec |
| ------- | ---- |
| **Bottom sheets** | Use for filters, confirmations, and detail actions on mobile; 400px wide on desktop. |
| **Swipe gestures** | Swipe to delete / resume in lists; reveal actions with visible affordances; never swipe-only critical actions. |
| **Pull to refresh** | Required on dashboard, requests, notifications, and history lists. |
| **Sticky input** | Chat input sticks above the keyboard; never hidden by it. |
| **Sticky send button** | Send / Stop always reachable near the input while streaming. |
| **Safe area insets** | Respect `env(safe-area-inset-*)` on notched devices (navbars, chat input, drawers). |
| **Keyboard safe layout** | Content resizes with the keyboard; focused inputs never obscured. |
| **Touch targets** | All tappable targets ≥ 44px (matches §8 `sm` rule). |
| **Thumb reach** | Primary actions within the lower / center thumb zone; hamburger left, actions right. |
| **Navigation drawer** | Off-canvas drawer with the same sidebar content + user card (§9.5). |
| **Responsive tables** | Tables collapse to stacked cards under `md` (§10.20). |
| **Offline banner** | Banner shown when offline; retry-aware; cached views still browsable. |

---

## 38. Component Naming Convention

**Rules:**

- **Primitives** (shadcn/ui) live in `components/ui/` as lowercase files: `button.tsx`, `card.tsx`, `dialog.tsx`.
- **Shared composites** use PascalCase names in `components/shared/`.
- **Feature composites** use PascalCase in their feature folder (`components/features/{feature}/`).
- One component per file; file name = component name; `.tsx` extension only.

| File | Type | Purpose |
| ---- | ---- | ------- |
| `Button.tsx` | Primitive | Shared button variants |
| `Card.tsx` | Primitive | Base card surface |
| `StatCard.tsx` | Shared | Stat tile (icon, label, value, delta) |
| `StatusBadge.tsx` | Shared | Request / agent status chip |
| `ConversationSidebar.tsx` | Feature (chat) | Chat history sidebar |
| `ChatMessage.tsx` | Feature (chat) | Single message bubble |
| `NotificationCard.tsx` | Feature (notifications) | Notification list item |
| `RequestTimeline.tsx` | Feature (requests) | Request status timeline |
| `FilterBar.tsx` | Shared | Filter chips + search + sort row |
| `EmptyState.tsx` | Shared | Icon + title + description + CTA (§34) |
| `LoadingSkeleton.tsx` | Shared | 1:1 layout skeleton |

---

## 39. Next.js App Router File Convention

| File | Purpose | When required |
| ---- | ------- | ------------- |
| `page.tsx` | Renders the route's UI | Every route; server-rendered by default. |
| `layout.tsx` | Shared shell for a route segment | Every segment that shares a shell (auth, dashboard, chat). |
| `loading.tsx` | Route-level loading UI (skeleton) | Every data-heavy route; must match the final layout (§10.24). |
| `error.tsx` | Route-level error UI with retry | Every route; client boundary, never raw errors. |
| `not-found.tsx` | 404 page for the segment | Root level always; per-segment for nested 404s. |
| `template.tsx` | Re-rendered layout (state reset per navigation) | Only when a fresh component instance is needed per navigation. |
| `default.tsx` | Parallel-route fallback | Required for parallel / conditional routes (e.g., modal patterns). |
| `route.ts` | API route handler | Only for server endpoints that do not belong in the FastAPI backend. |

---

## 40. Folder Naming Convention

One responsibility per folder — never mix concerns.

| Folder | Responsibility | Example contents |
| ------ | -------------- | ---------------- |
| `components/` | UI building blocks | `ui/`, `shared/`, `features/`, `layouts/` |
| `features/` | Feature modules | `chat/`, `dashboard/`, `requests/`, `notifications/` |
| `layouts/` | Shell layouts | `public-navbar/`, `app-sidebar/`, `auth-shell/` |
| `hooks/` | Custom React hooks | `useAuth`, `useChat`, `useMediaQuery` |
| `services/` | API client & data access | `api-client`, `chat-service`, `auth-service` |
| `lib/` | Utilities, helpers, shared logic | `utils`, `validators`, `format` |
| `types/` | Shared TypeScript types | `request.ts`, `chat.ts`, `user.ts` |
| `utils/` | Pure helper functions | `date`, `cn`, `slugify` |
| `config/` | Static configuration | `navigation.ts`, `features.ts` |
| `constants/` | Constant values | `routes`, `status-maps`, `agent-list` |
| `styles/` | Global styles & tokens | `globals.css`, `theme` |
| `assets/` | Static assets | images, fonts, illustrations |
| `providers/` | React providers | `ThemeProvider`, `AuthProvider` |
| `contexts/` | React contexts | `ChatContext`, `NotificationContext` |

---

## 41. UI Testing Checklist

| Category | Checklist |
| -------- | --------- |
| **Responsive** | Layouts verified at all breakpoints (§8); no horizontal overflow; content reflows correctly. |
| **Accessibility** | WCAG AA; color contrast; reduced-motion respected. |
| **Keyboard navigation** | Full tab order; arrow keys in menus / tabs; Esc closes overlays; focus never lost. |
| **Screen reader** | Semantic HTML; `aria-live` for chat / streaming / toasts; alt text; one `h1` per page. |
| **Focus states** | Visible 2px ring + 4px offset on every focusable element (§22). |
| **Loading** | Spinner / skeleton on every async view; no blank screens. |
| **Skeleton** | Matches the final layout 1:1; no layout shift on data arrival (CLS-safe). |
| **Empty state** | §34 spec present on every list / dashboard. |
| **Error state** | Friendly message + Retry; drafts preserved; no stack traces. |
| **Form validation** | Client + server; inline errors; disabled-until-valid; success feedback. |
| **Performance** | Budget met (§32); images optimized; code-split verified. |
| **Mobile** | ≥ 44px targets; sticky input; safe areas; drawer navigation; pull-to-refresh. |
| **Tablet** | Rail sidebar; 2-col grids; tables readable or card-ized. |
| **Desktop** | Full sidebar; 4-col stats; content ≤ 1280px. |
| **Theme ready** | Built on tokens / variables; no hardcoded colors; dark-mode swap clean. |
| **Reusable components** | No duplicated markup; new UI from the shared library only. |

---

## 42. Design Source Policy

- **This document replaces Figma.** No design file is required or referenced.
- The UI/UX Architecture Document is the **only** design source for the frontend.
- **All future frontend implementation must strictly follow this document** — pages, components, layouts, and interactions.
- **Any design modification must first update this document**, then code may follow.
- Discrepancies between code and this document are resolved in favor of this document.

---

## 43. AI Generated UI Rules

Every AI-generated UI **must**:

- **Reuse existing components** — build from the shared library only.
- **Never duplicate UI** — search before creating; extract shared parts.
- **Never hardcode colors** — design tokens only.
- **Always use design tokens** (§24) for color, spacing, radius, shadow, typography, motion.
- **Always use Tailwind CSS.**
- **Always use shadcn/ui.**
- **Always use strict TypeScript.**
- **Keep components modular** — one responsibility, composable.
- **Keep accessibility compliant** — WCAG AA from the first version.
- **Follow PROJECT_RULES.md.**
- **Follow ui-ux-design.md.**
- **Generate production-ready UI only** — no placeholders, no TODOs, no throwaway code.

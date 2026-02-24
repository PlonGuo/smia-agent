# AI Daily Intelligence Aggregator — Final Implementation Plan

## Context

SmIA currently supports **on-demand** analysis of any topic across Reddit, YouTube, and Amazon. This feature adds a **daily AI ecosystem intelligence digest** — aggregating updates from arXiv, GitHub Trending, RSS/Substack blogs, and Bluesky researcher posts, then using an LLM to categorize, score, and summarize them into a kanban-style report.

**Key design decisions** (confirmed with user):
- AI-ecosystem-first, extensible architecture for future topics
- **Lazy trigger**: no Vercel Cron — digest generated when first authorized user visits `/ai-daily-report` that day
- **One report per day**, shared across all authorized users, with race condition protection
- **Permission system**: Admin / Approved User / Regular User (3 roles)
- **Direct approval flow**: users request access → admin approves via admin page → email notification via Resend
- **LLM**: GPT-4.1 via PydanticAI (~$0.12/digest, best quality for synthesis and scoring)
- **30-day retention** with auto-cleanup + browsable history
- **Kanban UI** grouped by category with importance scoring

---

## Data Sources (4 Collectors)

| Source | Content | API/Library | Cost |
|--------|---------|-------------|------|
| **arXiv** | cs.AI + cs.LG papers (last 24h) | `arxiv` Python library | Free |
| **GitHub Trending** | New AI/LLM repos sorted by stars | GitHub Search API (httpx) | Free |
| **RSS/Substack/Blogs** | OpenAI, Anthropic, DeepMind, HuggingFace, Meta AI blogs + researcher Substacks (Lilian Weng, Simon Willison, Nathan Lambert, etc.) | `feedparser` | Free |
| **Bluesky** | Posts from ~20 top AI researchers | AT Protocol API (httpx) | Free |

Extensible: adding a new source = one collector file + one import line.

---

## Permission Model

| Role | Digest Page | Admin Page | Approve Requests |
|------|:-----------:|:----------:|:----------------:|
| **Admin** (`admins` table) | Yes | Yes | Yes |
| **Approved User** (`digest_authorized_users` table) | Yes | No | No |
| **Regular User** (neither) | Sees "Request Access" | No | No |

### Admin Seeding
`ADMIN_EMAIL` env var is used **only at bootstrap**: on first run, if the `admins` table is empty, seed it with the `ADMIN_EMAIL` value. After that, all admin management happens through the `/admin` page. All notification emails query the `admins` table for recipients — never rely on the env var at runtime.

### Access Request Flow
1. Regular user visits `/ai-daily-report` → "No Access" view + "Request Access" button
2. Modal: email (pre-filled from account) + reason textarea → Submit
3. Backend: saves to `digest_access_requests` with `status='pending'` + sends email to **all admins** (queried from `admins` table) via Resend
4. **User sees "pending" state**: page shows "Your request is pending approval" with status indicator (replaces "Request Access" button)
5. Admin visits `/admin` → pending requests table (Realtime: new requests appear automatically)
6. Admin clicks "Approve" → user added to `digest_authorized_users` + approval email to user
7. Admin clicks "Reject" → rejection email sent (optional reason), user can re-request
8. **User sees status change in real-time** via Supabase Realtime subscription on their `digest_access_requests` row

### User-Facing States on `/ai-daily-report`
| State | UI |
|-------|-----|
| **No request** | "Request Access" button + explanation |
| **Pending** | "Your request is pending approval" + status indicator + submitted date |
| **Rejected** | "Request denied" + reason (if provided) + "Request Again" button |
| **Approved** (or Admin) | Full digest content |

### Admin Page (`/admin`)
- Only accessible by users in `admins` table (multi-admin support)
- Tabs: "Access Requests" | "Manage Admins"
- Access Requests: table with email, reason, date, status, approve/reject buttons — **Realtime**: new requests appear automatically via Supabase subscription
- Manage Admins: list of current admins + "Add Admin" button
- Cost tracking: shows LLM token usage per digest

---

## Trigger Mechanism (Lazy, No Cron, No Manual Trigger)

Fully automatic — visiting the page triggers generation if needed. No regenerate button.

```
Authorized user visits /ai-daily-report
  → Frontend: GET /api/ai-daily-report/today
  → Backend: Check permission (admin OR authorized_users)
  → Backend: Call PostgreSQL RPC `claim_digest_generation(today)`
     → claimed=true  → return {status:'collecting', digest_id} IMMEDIATELY
                        then run pipeline in FastAPI BackgroundTask
     → claimed=false, status='collecting'/'analyzing' → return status (someone else is generating)
     → claimed=false, status='completed' → return cached digest immediately
  → Response returns FAST (<500ms) — never holds connection during generation

Frontend behavior:
  → status='completed' → render kanban immediately
  → status='collecting'/'analyzing' → show skeleton UI with progress stages
     → subscribe to `daily_digests` Realtime channel for status changes
     → update progress display based on Realtime events
     → when status='completed' → fetch full digest + render kanban
```

> **Architecture note (C1 — Vercel timeout):** The pipeline (4 collectors + LLM) can take 30-90s. Vercel serverless functions have a 60s default timeout (`maxDuration`). Instead of holding the HTTP connection open, the endpoint returns immediately after claiming the lock and runs the pipeline as a **FastAPI `BackgroundTask`** (same pattern as `api/routes/telegram.py` webhook). The frontend subscribes to Realtime for progress and fetches the completed digest when `status='completed'`. If the Vercel function is killed before completion, the stale lock timeout auto-reclaims.
>
> Consider increasing `maxDuration` in `vercel.json` to 120-300s (Vercel Pro) for the `/api/ai-daily-report/today` route to give the background pipeline more time.

### Race Condition Handling (PostgreSQL Atomic RPC)

A single PostgreSQL function handles all coordination. No check-then-act TOCTOU race possible:

```sql
-- NOTE (C3): Returns JSONB instead of TABLE for safer PostgREST serialization.
-- Supabase client: result = client.rpc("claim_digest_generation", {...}).execute()
-- Access: result.data → {"claimed": true, "digest_id": "...", "current_status": "collecting"}
CREATE FUNCTION claim_digest_generation(p_date DATE)
RETURNS JSONB
AS $$
DECLARE v_id UUID; v_status TEXT;
BEGIN
    -- 1. Reclaim stale locks (crashed generators, 150s timeout)
    -- Set to maxDuration * 2 + 30 to avoid reclaiming while still running
    UPDATE daily_digests SET status = 'failed', updated_at = NOW()
    WHERE digest_date = p_date
      AND status IN ('collecting', 'analyzing')
      AND updated_at < NOW() - INTERVAL '150 seconds';

    -- 2. Atomic claim: insert OR reclaim failed (single SQL operation)
    INSERT INTO daily_digests (digest_date, status, updated_at)
    VALUES (p_date, 'collecting', NOW())
    ON CONFLICT (digest_date) DO UPDATE
      SET status = 'collecting', updated_at = NOW()
      WHERE daily_digests.status = 'failed'
    RETURNING id INTO v_id;

    -- 3. Did we win?
    IF v_id IS NOT NULL THEN
        RETURN jsonb_build_object('claimed', true, 'digest_id', v_id, 'current_status', 'collecting');
    ELSE
        SELECT d.id, d.status INTO v_id, v_status
        FROM daily_digests d WHERE d.digest_date = p_date;
        RETURN jsonb_build_object('claimed', false, 'digest_id', v_id, 'current_status', v_status);
    END IF;
END;
$$ LANGUAGE plpgsql;
```

**Why this is bulletproof in serverless:**
- `INSERT ... ON CONFLICT` is atomic at the PostgreSQL row-lock level — even 100 simultaneous serverless functions, exactly ONE wins
- No separate "check" then "act" — single atomic SQL operation, no TOCTOU gap
- Stale lock recovery: if winning function crashes, 150s timeout auto-reclaims (`maxDuration * 2 + 30` to avoid reclaiming a legitimately running pipeline)

### Stage-Based Progress Tracking

The generating function updates the DB after each phase:
1. **INSERT** `status='collecting'` → 4 collectors run in parallel
2. **UPDATE** `status='analyzing'` → collectors done, LLM starts
3. **UPDATE** `status='completed'` → full digest data saved

Frontend maps status to progress UI:
```
┌────────────────────────────────────────────┐
│  ◉ Collecting from arXiv...        [done]  │
│  ◉ Collecting from GitHub...       [done]  │
│  ◉ Collecting from RSS/Substack... [done]  │
│  ◉ Collecting from Bluesky...   [running]  │
│  ○ Analyzing with AI...         [pending]  │
│  ○ Generating report...         [pending]  │
│                                            │
│  Usually takes 30-60 seconds               │
│  ████████████░░░░░░░░░  45%                │
│                                            │
│  [skeleton kanban cards shimmer below]     │
└────────────────────────────────────────────┘
```

| Scenario | Outcome |
|----------|---------|
| 1 user visits | Claims lock, generates, shows kanban |
| 10 users visit simultaneously | 1 generates; other 9 see progress UI, then kanban |
| Generator function crashes | After 150s, next user's request auto-reclaims |
| User visits later in the day | Digest already completed, instant kanban |

---

## LLM Analysis Features

The digest agent (PydanticAI, no tools) receives all collected items and produces:
- **Category** per item: Breakthrough | Research | Tooling | Open Source | Infrastructure | Product | Policy | Safety | Other
- **Importance score (1-5)** per item
- **"Why it matters"** sentence per item (10-200 chars)
- **Content deduplication**: identify same news across sources, merge into primary source with "Also on: X, Y"
- **Cross-source theme detection** in executive summary (e.g., "MoE trending across arXiv + GitHub")
- **Trending keywords/tags** extracted across all items
- **Top highlights** (3-5 most important items of the day)
- **Source health** report (which collectors succeeded/failed)

---

## Database Schema

### `daily_digests`
```
id              UUID PK DEFAULT gen_random_uuid()
digest_date     DATE UNIQUE
status          VARCHAR(20) — 'collecting' | 'analyzing' | 'completed' | 'failed'
executive_summary TEXT
items           JSONB (array of DigestItem)
top_highlights  JSONB (array of strings)
trending_keywords JSONB (array of strings)
category_counts JSONB
source_counts   JSONB
source_health   JSONB — {arxiv: "ok", github: "ok", rss: "ok", bluesky: "failed"}
total_items     INTEGER
model_used      VARCHAR(100)
processing_time_seconds INTEGER
langfuse_trace_id VARCHAR(255)
token_usage     JSONB
prompt_version  VARCHAR(50) — for LLM prompt versioning
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now() — used for stale lock detection (150s timeout)
```
RLS: authenticated users can SELECT (completed only), service role can ALL.
Indexes: `digest_date` (UNIQUE covers it), `status`.

### `digest_collector_cache`
```
id              UUID PK DEFAULT gen_random_uuid()
digest_date     DATE
source          VARCHAR(50)
items           JSONB
item_count      INTEGER
collected_at    TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE(digest_date, source)
```
RLS: service role only.

### `admins`
```
id              UUID PK DEFAULT gen_random_uuid()
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
email           TEXT NOT NULL UNIQUE
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```
RLS: service role can ALL, authenticated can SELECT own row.

### `digest_authorized_users`
```
id              UUID PK DEFAULT gen_random_uuid()
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
email           TEXT NOT NULL UNIQUE
approved_by     UUID REFERENCES admins(user_id)
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```
RLS: service role can ALL, authenticated can SELECT own row.

### `digest_access_requests`
```
id              UUID PK DEFAULT gen_random_uuid()
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
email           TEXT NOT NULL
reason          TEXT NOT NULL
status          VARCHAR(20) — 'pending' | 'approved' | 'rejected'
rejection_reason TEXT — optional reason when admin rejects (I6)
reviewed_by     UUID — admin user_id
reviewed_at     TIMESTAMPTZ
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```
RLS: service role can ALL, authenticated can INSERT own + SELECT own.
Indexes: `user_id` (for permission lookups), `status` (for admin filtering).

### `digest_bookmarks`
```
id              UUID PK DEFAULT gen_random_uuid()
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
digest_id       UUID REFERENCES daily_digests(id) ON DELETE CASCADE
item_url        TEXT NOT NULL — URL of the bookmarked item
item_title      TEXT
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE(user_id, item_url)
```
RLS: users can CRUD own rows.

### `digest_feedback`
```
id              UUID PK DEFAULT gen_random_uuid()
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
digest_id       UUID REFERENCES daily_digests(id) ON DELETE CASCADE
item_url        TEXT — NULL for overall digest feedback
vote            SMALLINT — 1 (thumbs up) or -1 (thumbs down)
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE(user_id, digest_id, item_url)
```
RLS: users can CRUD own rows.

### `digest_share_tokens`
```
id              UUID PK DEFAULT gen_random_uuid()
digest_id       UUID REFERENCES daily_digests(id) ON DELETE CASCADE
token           VARCHAR(64) UNIQUE — random share token
created_by      UUID REFERENCES auth.users(id)
expires_at      TIMESTAMPTZ — 7 days from creation
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```
RLS: service role can ALL.
**Cleanup (S5):** Expired share tokens cleaned up alongside 30-day digest cleanup — `DELETE FROM digest_share_tokens WHERE expires_at < NOW()`.

---

## New Files

### Backend (`api/`)

| File | Purpose |
|------|---------|
| `models/digest_schemas.py` | Pydantic models: `RawCollectorItem`, `DigestItem`, `DailyDigest`, feedback/bookmark/request schemas |
| `services/collectors/__init__.py` | Imports all collectors for self-registration |
| `services/collectors/base.py` | `Collector` Protocol, `COLLECTOR_REGISTRY`, `register_collector()` |
| `services/collectors/arxiv_collector.py` | arXiv cs.AI + cs.LG papers |
| `services/collectors/github_collector.py` | GitHub trending AI repos |
| `services/collectors/rss_collector.py` | RSS/Substack/blog feeds |
| `services/collectors/bluesky_collector.py` | Bluesky posts from AI researchers |
| `services/digest_agent.py` | PydanticAI agent: categorize, score, deduplicate, summarize |
| `services/digest_service.py` | Orchestrator: lazy trigger, race condition, caching, cleanup, Telegram notify |
| `services/email_service.py` | Resend API wrapper: send access request/approval/rejection emails |
| `routes/ai_daily_report.py` | AI Daily Report endpoints: `GET /today`, `GET /`, `GET /:id`, `GET /shared/:token` |
| `routes/admin.py` | Admin endpoints: requests CRUD, admins CRUD, digest stats |
| `routes/bookmarks.py` | Bookmark endpoints: `POST`, `DELETE`, `GET /my` |
| `routes/feedback.py` | Feedback endpoints: `POST /vote`, `GET /digest/:id/votes` |
| `cli/__init__.py` | Empty init |
| `cli/run_digest.py` | CLI: `cd api && uv run python -m cli.run_digest` |
| `config/rss_feeds.json` | (S2) Configurable RSS feed list — add/remove feeds without code changes |
| `migrations/002_add_digest_tables.sql` | All new tables |

### Frontend (`frontend/src/`)

| File | Purpose |
|------|---------|
| `pages/AiDailyReport.tsx` | Main report page: permission check (4 states) → kanban view, pending, rejected, or "request access" |
| `pages/AiDailyReportHistory.tsx` | Paginated history of past reports (last 30 days) |
| `pages/AiDailyReportDetail.tsx` | Full report detail view (for history items) |
| `pages/AiDailyReportShared.tsx` | Public shared view (no auth required, token-validated) |
| `pages/Admin.tsx` | Admin page: access requests + manage admins |
| `components/digest/KanbanBoard.tsx` | Kanban layout: columns by category, cards sorted by importance |
| `components/digest/KanbanCard.tsx` | Individual card: title, source badge, importance, insight, bookmark, vote |
| `components/digest/DigestHeader.tsx` | Executive summary, top highlights, trending tags, source health |
| `components/digest/DigestSkeleton.tsx` | Skeleton loading UI with progress stages |
| `components/digest/AccessRequestModal.tsx` | Modal: email + reason form |
| `components/digest/ExportButton.tsx` | Export as Markdown (S4: PDF deferred — adds heavy deps like jspdf+html2canvas) |
| `components/digest/ShareButton.tsx` | Generate + copy shareable link |
| `components/charts/CategoryBreakdown.tsx` | Recharts bar chart for category distribution |
| `components/admin/RequestsTable.tsx` | Table of access requests with approve/reject |
| `components/admin/AdminsManager.tsx` | Manage admin list |
| `hooks/useRealtimeSubscription.ts` | Generic Supabase Realtime subscription hook (mount/unmount lifecycle) |
| `hooks/useDigestPermissions.ts` | (S7) Digest-specific permission hook — only runs on digest pages, not globally |

### Shared

| File | Change |
|------|--------|
| `shared/types.ts` | Add all digest-related TypeScript interfaces |

---

## Modified Files

| File | Change |
|------|--------|
| `api/index.py` | Add digest, admin, bookmarks, feedback routers |
| `api/core/config.py` | Add `resend_api_key`, `admin_email` to Settings |
| `api/pyproject.toml` | Add `arxiv>=2.1.0`, `feedparser>=6.0.0`, `resend>=2.0.0` |
| `api/services/telegram_service.py` | Add `notify_digest_ready()` function |
| `api/services/database.py` | Add digest permission check helpers |
| `frontend/src/App.tsx` | Add routes: `/ai-daily-report`, `/ai-daily-report/history`, `/ai-daily-report/:id`, `/ai-daily-report/shared/:token`, `/admin` |
| `frontend/src/components/Layout.tsx` | Add "AI Daily Report" nav item (+ "Admin" for admin users) |
| `frontend/src/lib/api.ts` | Add all digest/admin/bookmark/feedback API functions |
| `frontend/src/hooks/useAuth.tsx` | ~~Add `isAdmin`/`hasDigestAccess`~~ → (S7) NOT modified. Use separate `useDigestPermissions` hook instead |
| `frontend/src/pages/Settings.tsx` | Refactor Telegram binding polling → Supabase Realtime subscription |

---

## Key Architecture Decisions

### 1. Separate Agent (no tools)
Collectors run deterministically (all 4, every time). The agent receives pre-collected items and outputs structured `DailyDigest`. No tool-calling overhead.

### 2. Collector Protocol + Registry
Each collector implements `Collector` Protocol. Self-registers on import. Adding a new source = one file + one import.

### 3. Lazy Trigger (no Cron)
Digest generated on first authorized user visit per day. No Vercel Cron config needed. Saves costs on days with no visitors.

### 4. Race Condition via PostgreSQL Atomic RPC
Single PostgreSQL function (`claim_digest_generation`) handles lock acquisition, stale detection (90s), and reclaim — all in one atomic operation. No TOCTOU race. Client-side Supabase Realtime subscription for progress tracking (replaces polling).

### 5. Content Deduplication
LLM identifies same news across sources and merges into one item with "Also on: X, Y" attribution.

### 6. Smart Retry
Collector results cached in `digest_collector_cache`. If LLM fails, retry only re-runs the LLM step, not all collectors.

### 7. 30-Day Auto-Cleanup
On each new digest generation, delete `daily_digests` and `digest_collector_cache` rows older than 30 days. Related bookmarks/feedback cascade-delete via FK constraints.

### 8. LLM Prompt Versioning
`prompt_version` field in `daily_digests` tracks which system prompt version was used. Enables quality comparison in Langfuse.

### 9. Supabase Realtime (No Polling)
All live-update scenarios use Supabase Realtime subscriptions instead of polling. A shared `useRealtimeSubscription` hook handles channel lifecycle.

| Scenario | Table | Event | Where Used | Replaces |
|----------|-------|-------|------------|----------|
| Digest generation progress | `daily_digests` | UPDATE (status change) | `AiDailyReport.tsx` | Would-be 3s polling |
| Access request status | `digest_access_requests` | UPDATE (status → approved/rejected) | `AiDailyReport.tsx` | Manual page refresh |
| Admin new request notification | `digest_access_requests` | INSERT | `Admin.tsx` | Manual refresh button |
| Telegram binding status | `user_bindings` | UPDATE (telegram_user_id set) | `Settings.tsx` | Existing 3s polling |

**Setup**: Enable Realtime publication on `daily_digests`, `digest_access_requests`, `user_bindings` via Supabase MCP (`ALTER PUBLICATION supabase_realtime ADD TABLE ...`). RLS policies allow authenticated SELECT on own rows — compatible with Realtime.

> **(S10) Scaling note:** Supabase free tier allows 200 concurrent Realtime connections. Each page with a subscription uses 1 connection (properly cleaned up on unmount via `useRealtimeSubscription`). Monitor concurrent connections if user base grows — upgrade to Pro tier if needed.

---

## Telegram Integration

When a digest completes generation:
1. Query all users in `admins` + `digest_authorized_users`
2. Join with `user_bindings` to find linked Telegram accounts
3. Send message to each: "Today's AI Digest is ready! X items across Y categories."
4. Auto-send, no opt-in required (linked Telegram = subscribed)

Reuses existing `telegram_service.py` infrastructure.

---

## Frontend Features

### Kanban Board
- Columns grouped by category (Breakthrough | Research | Tooling | etc.)
- Cards sorted by importance (1-5) within each column
- Each card: title (linked), source badge, importance stars, "why it matters", bookmark icon, thumbs up/down
- **Desktop**: multi-column kanban layout
- **Mobile**: filterable card list with category tabs (swipeable)

### Skeleton Loading
During generation (30-60s), show skeleton kanban with shimmer animation + progress stages:
"Collecting from arXiv... GitHub... RSS... Bluesky... Analyzing with AI..."

### Digest Header
- Executive summary
- Top highlights (bulleted)
- Trending keywords as clickable tags
- Source health dots (green = ok, red = failed)
- Category breakdown chart (Recharts bar)
- Share button + Export button (Markdown/PDF)

### History Page
- Paginated list of past digests (last 30 days)
- Each entry: date, summary preview, total items, category badges
- Click to view full digest detail

### Shared Digest View
- Public page at `/ai-daily-report/shared/:token` (no auth required)
- Token expires after 7 days
- Read-only view of the digest

---

## New Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RESEND_API_KEY` | Yes | Resend email API key (get from [resend.com](https://resend.com) → API Keys). Created with "all domains" scope — no domain verification needed. |
| `ADMIN_EMAIL` | Yes | **Bootstrap only**: used to seed the first admin row in `admins` table on first run. All runtime notifications query `admins` table instead. |
| `BLUESKY_APP_PASSWORD` | No | Optional: Bluesky app password for authenticated AT Protocol requests. Without it, uses public API (may be rate limited). Get from Bluesky Settings → App Passwords |

---

## Implementation Steps

> **For Claude:** Use `superpowers:executing-plans` to implement this plan task-by-task.
> **Pattern references:** Follow existing patterns in `api/routes/analyze.py`, `api/services/agent.py`, `api/models/schemas.py`. Check similar files before creating new ones.

---

### Step 1: Database Schema + Models

**Files to create:**
- `api/migrations/002_add_digest_tables.sql`
- `api/models/digest_schemas.py`

**Files to modify:**
- `shared/types.ts` (add digest TypeScript interfaces)

**1.1: Create migration SQL**

Create `api/migrations/002_add_digest_tables.sql` with all 8 tables from the Database Schema section above, plus the `claim_digest_generation()` RPC function from the Race Condition section. Include:
- All tables with constraints and FK references
- RLS policies as specified per table
- Indexes on `digest_date`, `user_id`, `status`
- The `claim_digest_generation(p_date DATE)` PostgreSQL function

**1.2: Run migration**

```bash
# Use Supabase MCP to execute the migration SQL
# OR run via Supabase SQL Editor in dashboard
```

**1.3: Enable Supabase Realtime**

Use **Supabase MCP** to enable Realtime publication (no manual dashboard steps):

```sql
-- Run via Supabase MCP SQL execution
ALTER PUBLICATION supabase_realtime ADD TABLE daily_digests;
ALTER PUBLICATION supabase_realtime ADD TABLE digest_access_requests;
-- user_bindings: check if already added, if not:
ALTER PUBLICATION supabase_realtime ADD TABLE user_bindings;
```

**1.4: Create Pydantic models**

Create `api/models/digest_schemas.py` — follow pattern from `api/models/schemas.py`:

```python
"""Pydantic models for AI Daily Report feature."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

# --- Collector models ---
class RawCollectorItem(BaseModel):
    title: str
    url: str
    source: str  # "arxiv", "github", "rss", "bluesky"
    snippet: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    extra: dict = Field(default_factory=dict)

# --- Digest output models (LLM structured output) ---
CategoryType = Literal[
    "Breakthrough", "Research", "Tooling", "Open Source",
    "Infrastructure", "Product", "Policy", "Safety", "Other"
]

class DigestItem(BaseModel):
    title: str
    url: str
    source: str
    category: CategoryType
    importance: int = Field(ge=1, le=5)
    why_it_matters: str = Field(min_length=10, max_length=200)
    also_on: list[str] = Field(default_factory=list)  # dedup attribution

# (I9) Separate LLM output from full DB row — agent only returns what LLM generates
class DailyDigestLLMOutput(BaseModel):
    """Structured output from PydanticAI agent — what the LLM generates."""
    executive_summary: str
    items: list[DigestItem]
    top_highlights: list[str] = Field(min_length=3, max_length=5)
    trending_keywords: list[str]
    category_counts: dict[str, int]
    source_counts: dict[str, int]

class DailyDigestDB(DailyDigestLLMOutput):
    """Full DB row — LLM output + metadata set by orchestrator."""
    id: str
    digest_date: str
    status: str
    source_health: dict[str, str]  # {arxiv: "ok", github: "failed", ...}
    total_items: int
    model_used: str
    processing_time_seconds: int
    langfuse_trace_id: str | None = None
    token_usage: dict | None = None
    prompt_version: str | None = None
    created_at: datetime
    updated_at: datetime

# --- API request/response models ---
class AccessRequestCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=500)

class AccessRequestResponse(BaseModel):
    id: str
    email: str
    reason: str
    status: Literal["pending", "approved", "rejected"]
    created_at: datetime

class DigestStatusResponse(BaseModel):
    status: Literal["collecting", "analyzing", "completed", "failed", "not_found"]
    digest_id: str | None = None
    digest: dict | None = None  # full digest data when completed

class BookmarkCreate(BaseModel):
    digest_id: str
    item_url: str
    item_title: str | None = None

class FeedbackCreate(BaseModel):
    digest_id: str
    item_url: str | None = None  # None = overall digest feedback
    vote: Literal[1, -1]
```

**1.5: Add TypeScript types**

Append to `shared/types.ts` — mirror the Pydantic models above as TypeScript interfaces.

**1.6: Seed admin**

```sql
-- Run once: seed first admin from ADMIN_EMAIL env var
-- This will be called from digest_service.py on first run
INSERT INTO admins (user_id, email)
SELECT id, email FROM auth.users WHERE email = '{ADMIN_EMAIL}'
ON CONFLICT (email) DO NOTHING;
```

**1.7: Write model unit tests**

```bash
cd api && uv run python -m pytest tests/test_models/ -v
```

---

### Step 2: Permission System + Email

**Files to create:**
- `api/services/email_service.py`
- `api/routes/admin.py`

**Files to modify:**
- `api/core/config.py` (add `resend_api_key`, `admin_email`)
- `api/services/database.py` (add permission helpers)

**2.1: Update config** — add to `Settings` class in `api/core/config.py`:

```python
# Email (Resend)
resend_api_key: str = ""
admin_email: str = ""  # Bootstrap only: seeds first admin
# Optional
bluesky_app_password: str = ""  # (S1) Optional Bluesky auth
```

**2.2: Create email service** — new pattern, full code:

```python
"""Email notifications via Resend API."""
import asyncio
import resend
from core.config import settings

resend.api_key = settings.resend_api_key

# (I5) resend.Emails.send() is synchronous — use sync functions.
# FastAPI auto-threads sync route dependencies, or call via run_in_executor.

def _send_email(to: str, subject: str, html: str):
    """Low-level sync send. Called from sync helpers or via run_in_executor."""
    resend.Emails.send({
        "from": "SmIA <onboarding@resend.dev>",
        "to": to,
        "subject": subject,
        "html": html,
    })

def send_access_request_notification(requester_email: str, reason: str, admin_emails: list[str]):
    """Notify all admins about a new access request."""
    for email in admin_emails:
        _send_email(
            to=email,
            subject=f"New AI Daily Report access request from {requester_email}",
            html=f"<p><b>{requester_email}</b> requested access.</p><p>Reason: {reason}</p><p><a href='/admin'>Review in admin panel</a></p>",
        )

def send_approval_email(user_email: str):
    """Notify user their access was approved."""
    _send_email(
        to=user_email,
        subject="Your AI Daily Report access has been approved",
        html="<p>You now have access to the AI Daily Report. <a href='/ai-daily-report'>View today's digest</a></p>",
    )

def send_rejection_email(user_email: str, reason: str | None = None):
    """Notify user their access was rejected."""
    reason_html = f"<p>Reason: {reason}</p>" if reason else ""
    _send_email(
        to=user_email,
        subject="AI Daily Report access request update",
        html=f"<p>Your access request was not approved.{reason_html}</p><p>You can submit a new request if needed.</p>",
    )
```

**2.3: Add permission helpers** to `api/services/database.py`:

```python
# NOTE (C2): All helpers are synchronous `def` — matching existing database.py pattern.
# The Supabase Python client is synchronous. FastAPI auto-runs sync dependencies
# in a thread pool, so these won't block the event loop.

def is_admin(user_id: str, access_token: str) -> bool:
    """Check if user is in admins table."""
    client = get_supabase_client(access_token)
    result = client.table("admins").select("id").eq("user_id", user_id).maybe_single().execute()
    return result is not None

def get_digest_access_status(user_id: str, access_token: str) -> str:
    """Returns: 'admin' | 'approved' | 'pending' | 'rejected' | 'none'"""
    if is_admin(user_id, access_token):
        return "admin"
    # Check digest_authorized_users
    client = get_supabase_client(access_token)
    authorized = client.table("digest_authorized_users").select("id").eq("user_id", user_id).maybe_single().execute()
    if authorized is not None:
        return "approved"
    # Check digest_access_requests (latest by created_at)
    request = client.table("digest_access_requests").select("status").eq("user_id", user_id).order("created_at", desc=True).limit(1).maybe_single().execute()
    if request is not None:
        return request.data["status"]  # 'pending' or 'rejected'
    return "none"

def get_all_admin_emails() -> list[str]:
    """Query admins table for all admin emails (service role)."""
    client = get_supabase_client()  # service role
    result = client.table("admins").select("email").execute()
    return [row["email"] for row in result.data]

def seed_admin_if_empty():
    """Bootstrap: if admins table is empty, seed with ADMIN_EMAIL. Idempotent."""
    client = get_supabase_client()  # service role
    count = client.table("admins").select("id", count="exact").execute()
    if count.count == 0 and settings.admin_email:
        # Find user by email in auth.users, insert into admins
        # Uses ON CONFLICT to be safe against races in serverless cold starts
        client.rpc("seed_admin", {"p_email": settings.admin_email}).execute()
```

**2.4: Create admin routes** — follow pattern from `api/routes/reports.py`:

```python
router = APIRouter(prefix="/api/admin", tags=["admin"])
# GET /api/admin/requests — list access requests (admin only)
# POST /api/admin/requests/:id/approve — approve request
# POST /api/admin/requests/:id/reject — reject request
# GET /api/admin/admins — list all admins
# POST /api/admin/admins — add new admin
# DELETE /api/admin/admins/:id — remove admin
```

**2.5: Write tests**

```bash
cd api && uv run python -m pytest tests/test_routes/test_admin.py tests/test_services/test_email.py -v
```

---

### Step 3: Collectors

**Files to create:**
- `api/services/collectors/__init__.py`
- `api/services/collectors/base.py`
- `api/services/collectors/arxiv_collector.py`
- `api/services/collectors/github_collector.py`
- `api/services/collectors/rss_collector.py`
- `api/services/collectors/bluesky_collector.py`

**Files to modify:**
- `api/pyproject.toml` (add `arxiv>=2.1.0`, `feedparser>=6.0.0`, `resend>=2.0.0`)

**3.1: Install dependencies**

```bash
cd api && uv add arxiv feedparser resend
```

**3.2: Create Collector Protocol + Registry** — new pattern, full code:

`api/services/collectors/base.py`:
```python
"""Collector Protocol and self-registration registry."""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from models.digest_schemas import RawCollectorItem

COLLECTOR_REGISTRY: dict[str, "Collector"] = {}

@runtime_checkable
class Collector(Protocol):
    name: str
    async def collect(self) -> list[RawCollectorItem]: ...

def register_collector(collector: Collector):
    """Register a collector instance. Called at import time."""
    COLLECTOR_REGISTRY[collector.name] = collector
```

**3.3: Create each collector** — key patterns:

`api/services/collectors/arxiv_collector.py`:
```python
"""arXiv cs.AI + cs.LG papers from last 24h."""
import asyncio
import arxiv
from langfuse import observe  # (I3)
from .base import register_collector, RawCollectorItem

class ArxivCollector:
    name = "arxiv"

    @observe(name="arxiv_collector")
    async def collect(self) -> list[RawCollectorItem]:
        # (I4) arxiv lib is synchronous — run in executor to avoid blocking event loop
        # Same pattern as fetch_reddit() in crawler.py
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._collect_sync)

    def _collect_sync(self) -> list[RawCollectorItem]:
        client = arxiv.Client()
        search = arxiv.Search(
            query="cat:cs.AI OR cat:cs.LG",
            max_results=50,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )
        items = []
        for result in client.results(search):
            items.append(RawCollectorItem(
                title=result.title,
                url=str(result.entry_id),
                source="arxiv",
                snippet=result.summary[:300],
                author=str(result.authors[0]) if result.authors else None,
                published_at=result.published,
            ))
        return items

register_collector(ArxivCollector())
```

> **Note (I4):** `feedparser.parse()` in `rss_collector.py` is also synchronous — wrap it in `run_in_executor` too. `github_collector.py` and `bluesky_collector.py` use `httpx.AsyncClient` which is natively async, no wrapping needed.

- `github_collector.py`: Use `httpx` + GitHub Search API (`created:>yesterday`, `topic:ai OR topic:llm`, sort by stars)
- `rss_collector.py`: Use `feedparser` with feed URLs. **(S2)** Store feed list in `api/config/rss_feeds.json` (not hardcoded in Python) for easy additions without code changes. Include: OpenAI blog, Anthropic blog, HuggingFace blog, Lilian Weng, Simon Willison, Nathan Lambert, etc. **(I4)** `feedparser.parse()` is synchronous — wrap in `run_in_executor`
- `bluesky_collector.py`: Use `httpx` + AT Protocol API to fetch posts from ~20 AI researcher handles. **(S1)** Add optional `BLUESKY_APP_PASSWORD` env var for authenticated requests (public API may rate limit aggressively)

**3.4: Self-registration** in `api/services/collectors/__init__.py`:
```python
"""Import all collectors to trigger self-registration."""
from . import arxiv_collector, github_collector, rss_collector, bluesky_collector
```

**3.5: Write collector unit tests** — mock external APIs, validate data structure and edge cases.

Test files to create:
- `api/tests/test_services/test_collectors/test_arxiv_collector.py`
- `api/tests/test_services/test_collectors/test_github_collector.py`
- `api/tests/test_services/test_collectors/test_rss_collector.py`
- `api/tests/test_services/test_collectors/test_bluesky_collector.py`
- `api/tests/test_services/test_collectors/test_collector_registry.py`

**Per-collector test requirements:**

**arXiv Collector:**
- Mock `arxiv.Client().results()` with sample paper data
- Assert returned items have: `title`, `url` (valid arXiv URL), `source="arxiv"`, `snippet` (≤300 chars), `author`, `published_at` (datetime)
- Test empty results (no papers in time window) → returns `[]`
- Test malformed paper entry (missing authors) → doesn't crash, `author=None`
- Test API error (network timeout) → raises or returns `[]` gracefully

**GitHub Trending Collector:**
- Mock `httpx.AsyncClient.get()` response with sample GitHub Search API JSON
- Assert items have: `title` (repo full_name), `url` (GitHub URL), `source="github"`, `snippet` (description), `author` (owner), `published_at` (created_at)
- Test pagination: API returns 30 results → all mapped correctly
- Test empty search results → returns `[]`
- Test rate limit response (HTTP 403) → handles gracefully
- Test repo with no description → `snippet=None` or empty string

**RSS/Blog Collector:**
- Mock `feedparser.parse()` with sample RSS XML for each feed
- Assert items have: `title`, `url` (valid link), `source="rss"`, `snippet` (entry summary, stripped HTML), `author`, `published_at`
- Test feed with no new entries (all older than 24h) → returns `[]`
- Test malformed feed (invalid XML) → skips feed, doesn't crash entire collector
- Test individual feed failure (one of N feeds down) → other feeds still collected
- Test HTML-in-summary stripping → clean text in snippet

**Bluesky Collector:**
- Mock `httpx.AsyncClient.get()` with sample AT Protocol API responses
- Assert items have: `title` (truncated post text), `url` (Bluesky post URL), `source="bluesky"`, `snippet`, `author` (handle), `published_at`
- Test researcher with no recent posts → skipped
- Test API auth failure → handles gracefully
- Test post with embedded link/quote → extracts correctly

**Registry tests (`test_collector_registry.py`):**
- Import `__init__.py` → all 4 collectors registered in `COLLECTOR_REGISTRY`
- Each registered collector has a unique `name`
- Each collector's `collect()` method is async callable
- `COLLECTOR_REGISTRY` returns dict with keys: `arxiv`, `github`, `rss`, `bluesky`

```bash
cd api && uv run python -m pytest tests/test_services/test_collectors/ -v
```

**3.6: Live smoke tests** — real API calls, run manually to verify data quality before integration.

Create `api/tests/test_services/test_collectors/test_collectors_live.py` (marked with `@pytest.mark.live`, excluded from CI):

```python
"""Live smoke tests for collectors — call real APIs.

Run manually: cd api && uv run python -m pytest tests/test_services/test_collectors/test_collectors_live.py -v -m live
"""
import pytest
from datetime import datetime, timedelta, timezone

pytestmark = pytest.mark.live  # skip in CI

@pytest.mark.asyncio
async def test_arxiv_live():
    """arXiv returns real papers from last 24h."""
    from services.collectors.arxiv_collector import ArxivCollector
    items = await ArxivCollector().collect()
    assert len(items) > 0, "arXiv returned no papers — check query or API"
    for item in items[:3]:
        assert item.source == "arxiv"
        assert item.title and len(item.title) > 5
        assert "arxiv.org" in item.url
        assert item.published_at is not None
        # Verify recency: published within last 48h (arXiv can lag)
        assert item.published_at > datetime.now(timezone.utc) - timedelta(hours=48)

@pytest.mark.asyncio
async def test_github_trending_live():
    """GitHub returns trending AI repos."""
    from services.collectors.github_collector import GithubCollector
    items = await GithubCollector().collect()
    assert len(items) > 0, "GitHub returned no repos — check API or query"
    for item in items[:3]:
        assert item.source == "github"
        assert "github.com" in item.url
        assert item.title  # repo name exists

@pytest.mark.asyncio
async def test_rss_live():
    """RSS feeds return blog posts."""
    from services.collectors.rss_collector import RssCollector
    items = await RssCollector().collect()
    assert len(items) > 0, "RSS returned no posts — check feed URLs"
    for item in items[:3]:
        assert item.source == "rss"
        assert item.url.startswith("http")
        assert item.title

@pytest.mark.asyncio
async def test_bluesky_live():
    """Bluesky returns posts from AI researchers."""
    from services.collectors.bluesky_collector import BlueskyCollector
    items = await BlueskyCollector().collect()
    assert len(items) > 0, "Bluesky returned no posts — check handles or API"
    for item in items[:3]:
        assert item.source == "bluesky"
        assert item.author  # researcher handle

@pytest.mark.asyncio
async def test_all_collectors_combined():
    """All 4 collectors return data, total > 20 items."""
    from services.collectors.base import COLLECTOR_REGISTRY
    from services.collectors import *  # trigger registration
    all_items = []
    for name, collector in COLLECTOR_REGISTRY.items():
        items = await collector.collect()
        print(f"  {name}: {len(items)} items")
        assert len(items) >= 0, f"{name} collector crashed"
        all_items.extend(items)
    assert len(all_items) > 20, f"Only {len(all_items)} total items — not enough for a useful digest"
    # Verify diversity: at least 3 sources contributed
    sources = set(item.source for item in all_items)
    assert len(sources) >= 3, f"Only {sources} contributed — expected at least 3 sources"
```

Add to `pyproject.toml` or `pytest.ini`:
```ini
[tool.pytest.ini_options]
markers = ["live: live API tests (deselect with '-m not live')"]
```

Run live smoke tests:
```bash
cd api && uv run python -m pytest tests/test_services/test_collectors/test_collectors_live.py -v -m live
```

---

### Step 4: Digest Agent

**Files to create:**
- `api/services/digest_agent.py`

**Follow pattern from:** `api/services/agent.py` (existing PydanticAI agent)

**4.1: Create digest agent** — PydanticAI agent, NO tools, structured output:

```python
"""PydanticAI agent for categorizing, scoring, and summarizing collected items."""
from pydantic_ai import Agent
from langfuse import observe  # (I3) Langfuse tracing
from models.digest_schemas import DailyDigestLLMOutput, RawCollectorItem

digest_agent = Agent(
    "openai:gpt-4.1",
    result_type=DailyDigestLLMOutput,  # (I9) Agent returns LLM output only, not full DB row
    system_prompt="""You are an AI research analyst. Given a list of items from arXiv, GitHub, RSS feeds, and Bluesky:

1. **Categorize** each item: Breakthrough | Research | Tooling | Open Source | Infrastructure | Product | Policy | Safety | Other
2. **Score importance** (1-5) based on potential impact
3. **Deduplicate**: If the same news appears from multiple sources, merge into one item with "also_on" attribution
4. **Extract trending keywords** across all items
5. **Write executive summary** highlighting cross-source themes (2-3 sentences)
6. **Select top 3-5 highlights** (most impactful items)
7. **Write "why it matters"** for each item (10-200 chars)

Be concise, precise, and focus on what practitioners care about.""",
)

@observe(name="analyze_digest")
async def analyze_digest(items: list[RawCollectorItem]) -> DailyDigestLLMOutput:
    """Run the digest agent on collected items."""
    items_text = "\n".join(
        f"[{i.source}] {i.title} — {i.snippet or 'no description'} ({i.url})"
        for i in items
    )
    result = await digest_agent.run(f"Analyze these {len(items)} items:\n\n{items_text}")
    return result.output  # NOTE (I2): PydanticAI v1.59 uses .output, not .data
```

**4.2: Write tests** — mock PydanticAI response:
```bash
cd api && uv run python -m pytest tests/test_services/test_digest_agent.py -v
```

---

### Step 5: Orchestration Service

**Files to create:**
- `api/services/digest_service.py`

**Files to modify:**
- `api/services/telegram_service.py` (add `notify_digest_ready()`)

**5.1: Create orchestrator** — core logic:

```python
"""Digest orchestrator: lazy trigger, race condition, caching, cleanup."""
import asyncio
import time
from langfuse import observe  # (I3) Langfuse tracing
from services.collectors.base import COLLECTOR_REGISTRY
from services.digest_agent import analyze_digest
from services.database import get_supabase_client, seed_admin_if_empty

def claim_or_get_digest(user_id: str, access_token: str) -> dict:
    """Claim lock or return current status. Called from GET /api/ai-daily-report/today.
    Returns FAST — does NOT run the pipeline. Pipeline runs in BackgroundTask (C1)."""
    client = get_supabase_client()
    today = date.today().isoformat()

    # 1. Claim via PostgreSQL RPC (returns JSONB — C3)
    result = client.rpc("claim_digest_generation", {"p_date": today}).execute()
    row = result.data  # JSONB: {"claimed": bool, "digest_id": "...", "current_status": "..."}

    if not row["claimed"]:
        if row["current_status"] == "completed":
            digest = client.table("daily_digests").select("*").eq("id", row["digest_id"]).single().execute()
            return {"status": "completed", "digest_id": row["digest_id"], "digest": digest.data}
        return {"status": row["current_status"], "digest_id": row["digest_id"]}

    # 2. We won the race — return immediately, pipeline runs in BackgroundTask
    return {"status": "collecting", "digest_id": row["digest_id"], "claimed": True}

@observe(name="run_digest_pipeline")
async def run_digest_pipeline(digest_id: str):
    """Background pipeline: collect → analyze → save. Runs in FastAPI BackgroundTask."""
    client = get_supabase_client()  # service role
    today = date.today().isoformat()
    try:
        # Collect (parallel)
        all_items, source_health = await _run_collectors(client, today)

        # Update status → analyzing
        client.table("daily_digests").update({"status": "analyzing", "updated_at": "now()"}).eq("id", digest_id).execute()

        # Analyze with LLM
        start = time.time()
        digest = await analyze_digest(all_items)
        processing_time = int(time.time() - start)

        # Save completed digest
        client.table("daily_digests").update({
            "status": "completed",
            "executive_summary": digest.executive_summary,
            "items": [item.model_dump() for item in digest.items],
            "top_highlights": digest.top_highlights,
            "trending_keywords": digest.trending_keywords,
            "category_counts": digest.category_counts,
            "source_counts": digest.source_counts,
            "source_health": source_health,
            "total_items": len(all_items),
            "model_used": "gpt-4.1",
            "processing_time_seconds": processing_time,
            "updated_at": "now()",
        }).eq("id", digest_id).execute()

        # Cleanup old digests (30 days) + expired share tokens (S5)
        _cleanup_old_digests(client)

        # Notify via Telegram
        await _notify_telegram(digest)
    except Exception as e:
        client.table("daily_digests").update({"status": "failed", "updated_at": "now()"}).eq("id", digest_id).execute()
        raise

async def _run_collectors(client, today: str) -> tuple[list, dict]:
    """Run all collectors in parallel, cache results."""
    # Check cache first (digest_collector_cache)
    # Run missing collectors via asyncio.gather
    # Save to cache
    ...

async def _cleanup_old_digests(client):
    """Delete digests older than 30 days."""
    ...
```

**5.2: Add Telegram notification** to `api/services/telegram_service.py`:
```python
async def notify_digest_ready(total_items: int, categories: dict):
    """Send digest notification to all authorized users with linked Telegram."""
    # Query admins + digest_authorized_users joined with user_bindings
    # Send message to each linked Telegram account
```

**5.3: Write tests:**
```bash
cd api && uv run python -m pytest tests/test_services/test_digest_service.py -v
```

---

### Step 6: API Endpoints + CLI

**Files to create:**
- `api/routes/ai_daily_report.py`
- `api/routes/bookmarks.py`
- `api/routes/feedback.py`
- `api/cli/__init__.py`
- `api/cli/run_digest.py`

**Files to modify:**
- `api/index.py` (register new routers)

**6.1: Create report routes** — follow `api/routes/reports.py` pattern.

> **(I8) Rate limiting:** Apply existing `check_rate_limit()` from `api/core/rate_limit.py` to abuse-prone endpoints:
> - `POST /api/ai-daily-report/access-request` — 3/hr per user (prevent spam)
> - `POST /api/ai-daily-report/share` — 10/hr per user (prevent token exhaustion)
> - `POST /api/bookmarks` — 50/hr per user
> - `POST /api/feedback/vote` — 50/hr per user
> - `GET /api/ai-daily-report/today` — 20/hr per user (prevent excessive generation triggers)

```python
from fastapi import BackgroundTasks
router = APIRouter(prefix="/api/ai-daily-report", tags=["ai-daily-report"])

@router.get("/today")
async def get_today_digest(
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Main endpoint: check permission → claim/return digest.
    Returns FAST. If claimed, pipeline runs in BackgroundTask (C1)."""
    status = get_digest_access_status(user.user_id, user.access_token)
    if status not in ("admin", "approved"):
        raise HTTPException(403, detail=f"Access status: {status}")
    result = claim_or_get_digest(user.user_id, user.access_token)
    if result.get("claimed"):
        background_tasks.add_task(run_digest_pipeline, result["digest_id"])
    return result

@router.get("/")
async def list_digests(page: int = 1, per_page: int = 20, ...):
    """List past digests (last 30 days)."""

@router.get("/{digest_id}")
async def get_digest(digest_id: str, ...):
    """Get specific digest by ID."""

@router.get("/shared/{token}")
async def get_shared_digest(token: str):
    """Public: get digest by share token (no auth required)."""

@router.post("/access-request")
async def request_access(body: AccessRequestCreate, user: AuthenticatedUser = Depends(get_current_user)):
    """Submit access request."""

@router.post("/share")
async def create_share_token(digest_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Generate shareable link."""
```

**6.2: Create bookmark + feedback routes** — simple CRUD, follow `reports.py` pattern.

**6.3: Register routers + admin seeding** in `api/index.py`:
```python
from routes.ai_daily_report import router as ai_daily_report_router
from routes.admin import router as admin_router
from routes.bookmarks import router as bookmarks_router
from routes.feedback import router as feedback_router
app.include_router(ai_daily_report_router)
app.include_router(admin_router)
app.include_router(bookmarks_router)
app.include_router(feedback_router)

# (I7) Bootstrap admin seeding on startup — idempotent, safe for concurrent cold starts
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    from services.database import seed_admin_if_empty
    seed_admin_if_empty()  # sync, runs once
    yield

# Pass lifespan to FastAPI app constructor: app = FastAPI(lifespan=lifespan, ...)
```

**6.4: Create CLI**

`api/cli/run_digest.py`:
```bash
cd api && uv run python -m cli.run_digest
```

**6.5: Write tests + smoke test:**
```bash
cd api && uv run python -m pytest tests/test_routes/test_ai_daily_report.py tests/test_routes/test_admin.py -v
```

---

### Step 7: Frontend — Realtime Hook + Permission + Admin

**Files to create:**
- `frontend/src/hooks/useRealtimeSubscription.ts`
- `frontend/src/components/digest/AccessRequestModal.tsx`
- `frontend/src/pages/Admin.tsx`
- `frontend/src/components/admin/RequestsTable.tsx`
- `frontend/src/components/admin/AdminsManager.tsx`

**Files to modify:**
- `frontend/src/hooks/useAuth.tsx` (add `isAdmin`, `hasDigestAccess`)
- `frontend/src/App.tsx` (add routes)
- `frontend/src/components/Layout.tsx` (add nav items)
- `frontend/src/lib/api.ts` (add API functions)
- `frontend/src/pages/Settings.tsx` (refactor polling → Realtime)

**7.1: Create Realtime hook** — new pattern, full code:

```typescript
// frontend/src/hooks/useRealtimeSubscription.ts
import { useEffect } from 'react';
import { supabase } from '../lib/supabase';
import type { RealtimePostgresChangesPayload } from '@supabase/supabase-js';

type ChangeEvent = 'INSERT' | 'UPDATE' | 'DELETE' | '*';

export function useRealtimeSubscription<T extends Record<string, unknown>>(
  table: string,
  event: ChangeEvent,
  callback: (payload: RealtimePostgresChangesPayload<T>) => void,
  filter?: string, // e.g. "user_id=eq.abc123"
) {
  useEffect(() => {
    const channel = supabase
      .channel(`${table}-${event}-${filter || 'all'}`)
      .on(
        'postgres_changes',
        { event, schema: 'public', table, filter },
        callback
      )
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [table, event, filter, callback]);
}
```

**7.2: Refactor Settings.tsx** — replace polling with Realtime:
```typescript
// Replace the setInterval polling block with:
useRealtimeSubscription('user_bindings', 'UPDATE', (payload) => {
  if (payload.new.telegram_user_id) {
    setBindingStatus('linked');
    setBindCode(null);
    toaster.success({ title: 'Telegram linked successfully!' });
  }
}, `user_id=eq.${user?.id}`);
```

**7.3: Create `useDigestPermissions` hook** instead of modifying `useAuth.tsx` (S7 — avoids extra Supabase query on every page load). This hook only runs on digest-related pages:
```typescript
// frontend/src/hooks/useDigestPermissions.ts
export function useDigestPermissions() {
  const { user } = useAuth();
  const [accessStatus, setAccessStatus] = useState<'loading'|'admin'|'approved'|'pending'|'rejected'|'none'>('loading');
  useEffect(() => {
    if (!user) return;
    api.getDigestAccessStatus().then(setAccessStatus);
  }, [user]);
  return { accessStatus, isAdmin: accessStatus === 'admin', hasAccess: ['admin', 'approved'].includes(accessStatus) };
}
```
Only call from `AiDailyReport.tsx` and `Admin.tsx` — NOT from `useAuth` (which runs globally).

**7.4: Create Admin page + components** — follow existing page patterns (Dashboard.tsx).

**7.5: Add routes to App.tsx** and nav items to Layout.tsx.

**7.6: Add API functions** to `frontend/src/lib/api.ts`.

---

### Step 8: Frontend — Kanban Digest View

**Files to create:**
- `frontend/src/pages/AiDailyReport.tsx`
- `frontend/src/components/digest/KanbanBoard.tsx`
- `frontend/src/components/digest/KanbanCard.tsx`
- `frontend/src/components/digest/DigestHeader.tsx`
- `frontend/src/components/digest/DigestSkeleton.tsx`
- `frontend/src/components/charts/CategoryBreakdown.tsx`

**8.1: Create AiDailyReport.tsx** — 4-state page:

```typescript
// Pseudo-structure:
export default function AiDailyReport() {
  const { user, isAdmin } = useAuth();
  const [accessStatus, setAccessStatus] = useState<string>('loading');
  const [digest, setDigest] = useState(null);

  // Fetch access status + today's digest on mount
  // Subscribe to Realtime: daily_digests (progress), digest_access_requests (approval)

  if (accessStatus === 'none') return <RequestAccessView />;
  if (accessStatus === 'pending') return <PendingView />;
  if (accessStatus === 'rejected') return <RejectedView />;
  if (!digest || digest.status !== 'completed') return <DigestSkeleton status={digest?.status} />;
  return <><DigestHeader digest={digest} /><KanbanBoard items={digest.items} /></>;
}
```

**8.2: KanbanBoard** — columns by category, cards sorted by importance within each column. **(S8)** Wrap each `KanbanCard` in an error boundary so one broken card doesn't crash the entire board.

**8.3: DigestSkeleton** — shimmer animation + stage-based progress indicator.

**8.4: CategoryBreakdown** — Recharts bar chart (follow existing `SentimentChart.tsx` pattern).

**8.5: Mobile responsive** — category tabs (swipeable) instead of columns on small screens.

---

### Step 9: Frontend — History, Sharing, Export

**Files to create:**
- `frontend/src/pages/AiDailyReportHistory.tsx`
- `frontend/src/pages/AiDailyReportDetail.tsx`
- `frontend/src/pages/AiDailyReportShared.tsx`
- `frontend/src/components/digest/ShareButton.tsx`
- `frontend/src/components/digest/ExportButton.tsx`

Follow patterns from Step 8. History page follows Dashboard.tsx pattern (paginated list). Detail page follows ReportDetail.tsx pattern. Shared page is a public route (no auth).

---

### Step 10: Weekly Rollup *(Deferred — separate plan)*

> **(S3)** This step is intentionally underspecified. It introduces new schema, aggregation pipeline, and frontend views. **Defer to a separate plan after daily digest is complete and validated.** Do not implement in this phase.

---

### Step 11: Integration Test + Polish

**11.1: Collector data pipeline integration test** — the most critical test. Verifies real data flows correctly through the entire pipeline.

Create `api/tests/test_integration/test_digest_pipeline.py`:

```python
"""Integration test: collectors → agent → structured digest output.

Tests the full data pipeline with MOCKED external APIs but REAL internal logic.
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
from models.digest_schemas import RawCollectorItem, DailyDigest

# --- Fixtures: realistic mock data per source ---

MOCK_ARXIV_ITEMS = [
    RawCollectorItem(title="Scaling Laws for Neural Language Models", url="https://arxiv.org/abs/2001.08361", source="arxiv", snippet="We study empirical scaling laws...", author="Kaplan et al.", published_at=datetime.now(timezone.utc)),
    RawCollectorItem(title="Attention Is All You Need v2", url="https://arxiv.org/abs/2401.00001", source="arxiv", snippet="We propose improvements to transformer architecture...", author="Research Team", published_at=datetime.now(timezone.utc)),
]

MOCK_GITHUB_ITEMS = [
    RawCollectorItem(title="openai/swarm", url="https://github.com/openai/swarm", source="github", snippet="Educational framework for multi-agent orchestration", author="openai", published_at=datetime.now(timezone.utc)),
]

MOCK_RSS_ITEMS = [
    RawCollectorItem(title="Anthropic Releases Claude 4.5", url="https://anthropic.com/blog/claude-4-5", source="rss", snippet="Today we release Claude 4.5 with improved reasoning...", author="Anthropic", published_at=datetime.now(timezone.utc)),
    RawCollectorItem(title="Anthropic Launches Claude 4.5", url="https://simonwillison.net/2025/anthropic-claude/", source="rss", snippet="Anthropic just released Claude 4.5, here are my thoughts...", author="Simon Willison", published_at=datetime.now(timezone.utc)),  # duplicate topic
]

MOCK_BLUESKY_ITEMS = [
    RawCollectorItem(title="Just published our new paper on efficient fine-tuning...", url="https://bsky.app/profile/researcher/post/abc", source="bluesky", snippet="Thread on LoRA improvements", author="researcher.bsky.social", published_at=datetime.now(timezone.utc)),
]

@pytest.mark.asyncio
async def test_full_pipeline_mock():
    """Collectors → merge → agent → DailyDigest with correct structure."""
    from services.collectors.base import COLLECTOR_REGISTRY

    # Mock all 4 collectors
    mock_collectors = {
        "arxiv": AsyncMock(collect=AsyncMock(return_value=MOCK_ARXIV_ITEMS)),
        "github": AsyncMock(collect=AsyncMock(return_value=MOCK_GITHUB_ITEMS)),
        "rss": AsyncMock(collect=AsyncMock(return_value=MOCK_RSS_ITEMS)),
        "bluesky": AsyncMock(collect=AsyncMock(return_value=MOCK_BLUESKY_ITEMS)),
    }

    with patch.dict(COLLECTOR_REGISTRY, mock_collectors, clear=True):
        # Step 1: Collect from all sources
        all_items = []
        for name, collector in COLLECTOR_REGISTRY.items():
            items = await collector.collect()
            all_items.extend(items)

        # Verify collection
        assert len(all_items) == 6  # 2 + 1 + 2 + 1
        sources = {item.source for item in all_items}
        assert sources == {"arxiv", "github", "rss", "bluesky"}

        # Step 2: Feed to agent (mock the LLM call, verify input/output contract)
        with patch("services.digest_agent.digest_agent.run") as mock_agent:
            mock_agent.return_value = AsyncMock(data=DailyDigest(
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                executive_summary="Major releases from Anthropic and new scaling research.",
                items=[],  # simplified for test
                highlights=[],
                trending_keywords=["claude", "scaling", "fine-tuning"],
                source_counts={"arxiv": 2, "github": 1, "rss": 2, "bluesky": 1},
                total_items=6,
            ))

            from services.digest_agent import analyze_digest
            result = await analyze_digest(all_items)

            # Verify agent was called with all items
            mock_agent.assert_called_once()
            call_args = mock_agent.call_args[0][0]
            assert "arxiv" in call_args
            assert "github" in call_args
            assert "bluesky" in call_args

            # Verify output structure
            assert isinstance(result, DailyDigest)
            assert result.total_items == 6
            assert len(result.trending_keywords) > 0
            assert result.executive_summary

@pytest.mark.asyncio
async def test_single_collector_failure_doesnt_block_others():
    """If one collector crashes, the rest still contribute to the digest."""
    from services.collectors.base import COLLECTOR_REGISTRY

    mock_collectors = {
        "arxiv": AsyncMock(collect=AsyncMock(return_value=MOCK_ARXIV_ITEMS)),
        "github": AsyncMock(collect=AsyncMock(side_effect=Exception("GitHub API rate limited"))),
        "rss": AsyncMock(collect=AsyncMock(return_value=MOCK_RSS_ITEMS)),
        "bluesky": AsyncMock(collect=AsyncMock(return_value=MOCK_BLUESKY_ITEMS)),
    }

    with patch.dict(COLLECTOR_REGISTRY, mock_collectors, clear=True):
        all_items = []
        for name, collector in COLLECTOR_REGISTRY.items():
            try:
                items = await collector.collect()
                all_items.extend(items)
            except Exception:
                pass  # orchestrator should handle this

        # 3 of 4 collectors succeeded
        assert len(all_items) == 5  # 2 + 0 + 2 + 1
        sources = {item.source for item in all_items}
        assert "github" not in sources
        assert len(sources) == 3  # still enough for a useful digest

@pytest.mark.asyncio
async def test_all_collectors_fail():
    """If all collectors fail, no digest is generated (graceful empty state)."""
    from services.collectors.base import COLLECTOR_REGISTRY

    mock_collectors = {
        "arxiv": AsyncMock(collect=AsyncMock(side_effect=Exception("timeout"))),
        "github": AsyncMock(collect=AsyncMock(side_effect=Exception("rate limit"))),
        "rss": AsyncMock(collect=AsyncMock(side_effect=Exception("DNS failure"))),
        "bluesky": AsyncMock(collect=AsyncMock(side_effect=Exception("auth error"))),
    }

    with patch.dict(COLLECTOR_REGISTRY, mock_collectors, clear=True):
        all_items = []
        for name, collector in COLLECTOR_REGISTRY.items():
            try:
                items = await collector.collect()
                all_items.extend(items)
            except Exception:
                pass
        assert len(all_items) == 0
        # Orchestrator should NOT call the agent and should set status to "failed"

@pytest.mark.asyncio
async def test_data_quality_validation():
    """All collected items pass schema validation — no None titles, no invalid URLs."""
    all_items = MOCK_ARXIV_ITEMS + MOCK_GITHUB_ITEMS + MOCK_RSS_ITEMS + MOCK_BLUESKY_ITEMS
    for item in all_items:
        assert item.title and len(item.title) > 0, f"Empty title from {item.source}"
        assert item.url.startswith("http"), f"Invalid URL from {item.source}: {item.url}"
        assert item.source in ("arxiv", "github", "rss", "bluesky")
        assert item.published_at is not None, f"Missing timestamp from {item.source}"
```

Run integration tests:
```bash
cd api && uv run python -m pytest tests/test_integration/test_digest_pipeline.py -v
```

**11.2: Live end-to-end smoke test** (manual, before deploy):
```bash
# Run all 4 live collector tests — verify real APIs return data
cd api && uv run python -m pytest tests/test_services/test_collectors/test_collectors_live.py -v -m live

# Check output quality: print sample items from each source
cd api && uv run python -c "
import asyncio
from services.collectors.base import COLLECTOR_REGISTRY
from services.collectors import *

async def main():
    for name, c in COLLECTOR_REGISTRY.items():
        items = await c.collect()
        print(f'\n=== {name}: {len(items)} items ===')
        for item in items[:2]:
            print(f'  {item.title[:80]}')
            print(f'    URL: {item.url}')
            print(f'    Published: {item.published_at}')

asyncio.run(main())
"
```

**11.3: E2E flow tests:**
- Run full E2E: visit `/ai-daily-report` → permission check → generation → kanban display
- Test access request flow end-to-end (all 4 states: no request → pending → approved/rejected)
- Test Realtime: verify all 4 subscriptions work (digest progress, request status, admin notifications, Telegram binding)
- Test shared link flow
- Verify Langfuse traces + cost tracking
- Verify Telegram notifications
- Verify 30-day cleanup

**11.4: Run all unit tests:**
```bash
cd api && uv run python -m pytest -v
```

**11.5: Wrap up:**
- Update `docs/features.md` and `claude-progress.txt`
- Archive progress: `mv claude-progress.txt docs/archive/claude-progress-ai-daily-report.txt`
- Update `CLAUDE.md` Plans Index: `ai-daily-digest.md` → `Done`

---

## Verification Checklist

1. **Unit tests**: `cd api && uv run python -m pytest tests/ -v` — all pass
2. **Permission flow (4 states)**: no request → "Request Access" → pending → admin approves → user sees digest; also test rejected → re-request
3. **Lazy trigger**: first visit generates, second visit returns cache, concurrent visits don't duplicate
4. **Race condition**: simulate 3 concurrent requests — only 1 generation occurs
5. **Collector unit tests**: each of 4 collectors tested with mocked APIs — correct `RawCollectorItem` fields, empty results, error handling
6. **Collector live smoke tests**: `pytest -m live` — all 4 sources return real data, >20 total items, ≥3 sources contributing
7. **Collector resilience**: single collector failure doesn't block others; all-fail triggers graceful empty state
8. **Pipeline integration**: collectors → agent produces valid `DailyDigest` with correct `source_counts` and `total_items`
9. **Deduplication**: same news from 2 sources appears as 1 item with attribution
10. **Kanban UI**: columns render, sorted by importance, responsive on mobile
11. **Skeleton loading**: shows progress stages during generation
12. **History**: past 30 days visible, older auto-deleted
13. **Share**: generate link, open in incognito → digest visible without auth
14. **Export**: download as Markdown, content matches display
15. **Bookmarks + Feedback**: save item, vote, persist across sessions
16. **Telegram**: authorized users with linked TG receive notification
17. **Langfuse**: traces for collectors + agent + full pipeline visible
18. **Admin page**: view requests (Realtime: new requests appear live), approve/reject, manage admins
19. **Realtime — Digest progress**: subscribe to `daily_digests` status changes, UI updates without polling
20. **Realtime — Access request**: user sees approval/rejection in real-time without refresh
21. **Realtime — Admin notifications**: new access requests appear on admin page without manual refresh
22. **Realtime — Telegram binding**: Settings page updates instantly when Telegram bot completes binding (replaces 3s polling)

---

## Review Notes (Applied 2026-02-24)

All issues from senior SDE review have been incorporated into the plan above. Summary of changes:

### Critical Fixes (C1-C3)
- **C1**: Digest pipeline runs in `FastAPI.BackgroundTask` — endpoint returns in <500ms, frontend subscribes to Realtime for progress. Avoids Vercel 60s timeout.
- **C2**: All new `database.py` helpers are synchronous `def` (matching existing pattern). Supabase Python client is sync; FastAPI auto-threads sync dependencies.
- **C3**: `claim_digest_generation` RPC returns `JSONB` instead of `TABLE` for predictable PostgREST serialization.

### Important Fixes (I1-I9)
- **I1**: All tables have `DEFAULT gen_random_uuid()` for PK and `DEFAULT now()` for timestamps.
- **I2**: `result.output` (not `result.data`) — matches PydanticAI v1.59 API.
- **I3**: `@observe` decorators on `analyze_digest()`, `run_digest_pipeline()`, `arxiv_collector.collect()`.
- **I4**: arXiv + feedparser (sync libs) wrapped in `run_in_executor` — same pattern as `fetch_reddit()` in existing `crawler.py`.
- **I5**: Email service uses sync `def` functions — `resend.Emails.send()` is synchronous.
- **I6**: `rejection_reason TEXT` column added to `digest_access_requests`.
- **I7**: `seed_admin_if_empty()` wired to FastAPI `lifespan` in `index.py`. Idempotent via `ON CONFLICT`.
- **I8**: Rate limits added for abuse-prone endpoints (access request 3/hr, share 10/hr, etc.).
- **I9**: `DailyDigestLLMOutput` (agent returns) vs `DailyDigestDB` (full row with metadata) — clean separation.

### Suggestions Applied (S1-S10)
- **S1**: Optional `BLUESKY_APP_PASSWORD` env var for authenticated AT Protocol.
- **S2**: RSS feeds stored in `api/config/rss_feeds.json` (not hardcoded).
- **S3**: Step 10 (Weekly Rollup) deferred to separate plan.
- **S4**: Export starts as Markdown-only; PDF deferred (heavy deps).
- **S5**: Expired share tokens cleaned up alongside 30-day digest cleanup.
- **S6**: Index on `digest_access_requests.user_id` and `status`.
- **S7**: `useDigestPermissions` hook (separate from `useAuth`) — only runs on digest pages.
- **S8**: Error boundary wraps each `KanbanCard` to prevent one broken card crashing the board.
- **S9**: Stale lock timeout increased from 90s to 150s (`maxDuration * 2 + 30`).
- **S10**: Supabase free tier 200 Realtime connection limit noted as scaling consideration.

---

## User Action Items (Before Implementation)

These are things **you (the developer)** need to set up manually — Claude cannot do these for you.

### 1. Resend Email Service (Required) — DONE

API key already created with "all domains" scope. No domain verification needed.

| Step | Action |
|------|--------|
| 1 | ~~Go to [resend.com](https://resend.com) and create a free account~~ ✅ Done |
| 2 | ~~Create API Key with "all domains" scope~~ ✅ Done |
| 3 | Add to `local.env`: `RESEND_API_KEY=re_xxxxxxxxxxxxx` (already have it) |
| 4 | Add to Vercel env vars for production (use Vercel MCP) |

> **Free tier**: 100 emails/day. Emails sent from `onboarding@resend.dev` (Resend's shared domain). Sufficient for this feature.

### 2. Admin Email Bootstrap (Required)

| Step | Action |
|------|--------|
| 1 | Add to `local.env`: `ADMIN_EMAIL=your@email.com` (must match a registered Supabase auth user) |
| 2 | Add to Vercel env vars for production |

> This email will be auto-seeded as the first admin on first app startup. After that, manage admins via `/admin` page.

### 3. Bluesky App Password (Optional)

| Step | Action |
|------|--------|
| 1 | Log into [bsky.app](https://bsky.app) |
| 2 | Go to Settings → App Passwords → Add App Password |
| 3 | Add to `local.env`: `BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx` |

> Without this, the Bluesky collector uses the public API which may be rate limited. Not required for development — can be added later.

### 4. Supabase Realtime (Required — automated via Supabase MCP)

> **No manual action needed.** Claude will enable Realtime publication using Supabase MCP during Step 1.3. The SQL commands (`ALTER PUBLICATION supabase_realtime ADD TABLE ...`) will be executed automatically after the migration creates the new tables.

### 5. Vercel `maxDuration` (Recommended — automated via Vercel MCP)

> **No manual action needed.** Claude will configure `maxDuration` in `vercel.json` and deploy using Vercel MCP. If on Vercel Pro, the digest endpoint will be set to 120-300s. On Vercel Hobby (free), the BackgroundTask pattern handles this, but very large digests may time out at 60s.

### Summary: What to add to `local.env`

```bash
# AI Daily Report — new env vars
RESEND_API_KEY=re_xxxxxxxxxxxxx          # Required: from resend.com (all domains scope)
ADMIN_EMAIL=your@email.com               # Required: bootstrap admin (must match Supabase auth user)
BLUESKY_APP_PASSWORD=                    # Optional: for authenticated Bluesky API
```

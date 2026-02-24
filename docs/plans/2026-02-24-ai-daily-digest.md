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
     → claimed=true, status='collecting' → you won the race, start pipeline
     → claimed=false, status='collecting'/'analyzing' → another instance is generating
     → claimed=false, status='completed' → return cached digest immediately
  → Return response with status

Frontend behavior:
  → status='completed' → render kanban immediately
  → status='collecting'/'analyzing' → show skeleton UI with progress stages
     → subscribe to `daily_digests` Realtime channel for status changes
     → update progress display based on Realtime events
     → when status='completed' → render kanban
```

### Race Condition Handling (PostgreSQL Atomic RPC)

A single PostgreSQL function handles all coordination. No check-then-act TOCTOU race possible:

```sql
CREATE FUNCTION claim_digest_generation(p_date DATE)
RETURNS TABLE(claimed BOOLEAN, digest_id UUID, current_status TEXT)
AS $$
DECLARE v_id UUID; v_status TEXT;
BEGIN
    -- 1. Reclaim stale locks (crashed generators, 90s timeout)
    UPDATE daily_digests SET status = 'failed', updated_at = NOW()
    WHERE digest_date = p_date
      AND status IN ('collecting', 'analyzing')
      AND updated_at < NOW() - INTERVAL '90 seconds';

    -- 2. Atomic claim: insert OR reclaim failed (single SQL operation)
    INSERT INTO daily_digests (digest_date, status, updated_at)
    VALUES (p_date, 'collecting', NOW())
    ON CONFLICT (digest_date) DO UPDATE
      SET status = 'collecting', updated_at = NOW()
      WHERE daily_digests.status = 'failed'
    RETURNING id INTO v_id;

    -- 3. Did we win?
    IF v_id IS NOT NULL THEN
        RETURN QUERY SELECT true, v_id, 'collecting'::TEXT;
    ELSE
        SELECT d.id, d.status INTO v_id, v_status
        FROM daily_digests d WHERE d.digest_date = p_date;
        RETURN QUERY SELECT false, v_id, v_status;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

**Why this is bulletproof in serverless:**
- `INSERT ... ON CONFLICT` is atomic at the PostgreSQL row-lock level — even 100 simultaneous serverless functions, exactly ONE wins
- No separate "check" then "act" — single atomic SQL operation, no TOCTOU gap
- Stale lock recovery: if winning function crashes, 90s timeout auto-reclaims (Vercel functions max 60s, so a crash is guaranteed dead within 60s)

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
| Generator function crashes | After 90s, next user's request auto-reclaims |
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
id              UUID PK
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
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ — used for stale lock detection (90s timeout)
```
RLS: authenticated users can SELECT (completed only), service role can ALL.

### `digest_collector_cache`
```
id              UUID PK
digest_date     DATE
source          VARCHAR(50)
items           JSONB
item_count      INTEGER
collected_at    TIMESTAMPTZ
UNIQUE(digest_date, source)
```
RLS: service role only.

### `admins`
```
id              UUID PK
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
email           TEXT NOT NULL UNIQUE
created_at      TIMESTAMPTZ
```
RLS: service role can ALL, authenticated can SELECT own row.

### `digest_authorized_users`
```
id              UUID PK
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
email           TEXT NOT NULL UNIQUE
approved_by     UUID REFERENCES admins(user_id)
created_at      TIMESTAMPTZ
```
RLS: service role can ALL, authenticated can SELECT own row.

### `digest_access_requests`
```
id              UUID PK
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
email           TEXT NOT NULL
reason          TEXT NOT NULL
status          VARCHAR(20) — 'pending' | 'approved' | 'rejected'
reviewed_by     UUID — admin user_id
reviewed_at     TIMESTAMPTZ
created_at      TIMESTAMPTZ
```
RLS: service role can ALL, authenticated can INSERT own + SELECT own.

### `digest_bookmarks`
```
id              UUID PK
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
digest_id       UUID REFERENCES daily_digests(id) ON DELETE CASCADE
item_url        TEXT NOT NULL — URL of the bookmarked item
item_title      TEXT
created_at      TIMESTAMPTZ
UNIQUE(user_id, item_url)
```
RLS: users can CRUD own rows.

### `digest_feedback`
```
id              UUID PK
user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE
digest_id       UUID REFERENCES daily_digests(id) ON DELETE CASCADE
item_url        TEXT — NULL for overall digest feedback
vote            SMALLINT — 1 (thumbs up) or -1 (thumbs down)
created_at      TIMESTAMPTZ
UNIQUE(user_id, digest_id, item_url)
```
RLS: users can CRUD own rows.

### `digest_share_tokens`
```
id              UUID PK
digest_id       UUID REFERENCES daily_digests(id) ON DELETE CASCADE
token           VARCHAR(64) UNIQUE — random share token
created_by      UUID REFERENCES auth.users(id)
expires_at      TIMESTAMPTZ — 7 days from creation
created_at      TIMESTAMPTZ
```
RLS: service role can ALL.

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
| `components/digest/ExportButton.tsx` | Export as Markdown or PDF |
| `components/digest/ShareButton.tsx` | Generate + copy shareable link |
| `components/charts/CategoryBreakdown.tsx` | Recharts bar chart for category distribution |
| `components/admin/RequestsTable.tsx` | Table of access requests with approve/reject |
| `components/admin/AdminsManager.tsx` | Manage admin list |
| `hooks/useRealtimeSubscription.ts` | Generic Supabase Realtime subscription hook (mount/unmount lifecycle) |

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
| `frontend/src/hooks/useAuth.tsx` | Add `isAdmin` and `hasDigestAccess` flags (fetched on auth) |
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

**Setup**: Enable Realtime publication on `daily_digests`, `digest_access_requests`, `user_bindings` in Supabase Dashboard. RLS policies allow authenticated SELECT on own rows — compatible with Realtime.

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
| `RESEND_API_KEY` | Yes | Resend email API key (get from [resend.com](https://resend.com) → API Keys) |
| `ADMIN_EMAIL` | Yes | **Bootstrap only**: used to seed the first admin row in `admins` table on first run. All runtime notifications query `admins` table instead. |

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

In Supabase Dashboard → Database → Replication, enable Realtime publication on:
- `daily_digests`
- `digest_access_requests`
- `user_bindings` (already exists, just enable Realtime)

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

class DailyDigest(BaseModel):
    executive_summary: str
    items: list[DigestItem]
    top_highlights: list[str] = Field(min_length=3, max_length=5)
    trending_keywords: list[str]
    category_counts: dict[str, int]
    source_counts: dict[str, int]

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
```

**2.2: Create email service** — new pattern, full code:

```python
"""Email notifications via Resend API."""
import resend
from core.config import settings

resend.api_key = settings.resend_api_key

async def send_access_request_notification(requester_email: str, reason: str, admin_emails: list[str]):
    """Notify all admins about a new access request."""
    for email in admin_emails:
        resend.Emails.send({
            "from": "SmIA <noreply@yourdomain.com>",
            "to": email,
            "subject": f"New AI Daily Report access request from {requester_email}",
            "html": f"<p><b>{requester_email}</b> requested access.</p><p>Reason: {reason}</p><p>Review at /admin</p>"
        })

async def send_approval_email(user_email: str):
    """Notify user their access was approved."""
    resend.Emails.send({
        "from": "SmIA <noreply@yourdomain.com>",
        "to": user_email,
        "subject": "Your AI Daily Report access has been approved",
        "html": "<p>You now have access to the AI Daily Report. Visit /ai-daily-report to see today's digest.</p>"
    })

async def send_rejection_email(user_email: str, reason: str | None = None):
    """Notify user their access was rejected."""
    # Similar pattern
```

**2.3: Add permission helpers** to `api/services/database.py`:

```python
async def is_admin(user_id: str, access_token: str) -> bool:
    """Check if user is in admins table."""
    client = get_supabase_client(access_token)
    result = client.table("admins").select("id").eq("user_id", user_id).maybe_single().execute()
    return result is not None

async def get_digest_access_status(user_id: str, access_token: str) -> str:
    """Returns: 'admin' | 'approved' | 'pending' | 'rejected' | 'none'"""
    if await is_admin(user_id, access_token):
        return "admin"
    # Check digest_authorized_users
    # Check digest_access_requests (latest)
    # Return appropriate status

async def get_all_admin_emails() -> list[str]:
    """Query admins table for all admin emails (service role)."""
    client = get_supabase_client()  # service role
    result = client.table("admins").select("email").execute()
    return [row["email"] for row in result.data]

async def seed_admin_if_empty():
    """Bootstrap: if admins table is empty, seed with ADMIN_EMAIL."""
    client = get_supabase_client()
    count = client.table("admins").select("id", count="exact").execute()
    if count.count == 0 and settings.admin_email:
        # Find user by email in auth.users, insert into admins
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
import arxiv
from .base import register_collector, RawCollectorItem

class ArxivCollector:
    name = "arxiv"
    async def collect(self) -> list[RawCollectorItem]:
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

- `github_collector.py`: Use `httpx` + GitHub Search API (`created:>yesterday`, `topic:ai OR topic:llm`, sort by stars)
- `rss_collector.py`: Use `feedparser` with hardcoded feed URLs (OpenAI blog, Anthropic blog, HuggingFace blog, Lilian Weng, Simon Willison, etc.)
- `bluesky_collector.py`: Use `httpx` + AT Protocol API to fetch posts from ~20 AI researcher handles

**3.4: Self-registration** in `api/services/collectors/__init__.py`:
```python
"""Import all collectors to trigger self-registration."""
from . import arxiv_collector, github_collector, rss_collector, bluesky_collector
```

**3.5: Write collector tests** — mock external APIs with `unittest.mock.patch`:
```bash
cd api && uv run python -m pytest tests/test_services/test_collectors/ -v
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
from models.digest_schemas import DailyDigest, RawCollectorItem

digest_agent = Agent(
    "openai:gpt-4.1",
    result_type=DailyDigest,
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

async def analyze_digest(items: list[RawCollectorItem]) -> DailyDigest:
    """Run the digest agent on collected items."""
    items_text = "\n".join(
        f"[{i.source}] {i.title} — {i.snippet or 'no description'} ({i.url})"
        for i in items
    )
    result = await digest_agent.run(f"Analyze these {len(items)} items:\n\n{items_text}")
    return result.data
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
from services.collectors.base import COLLECTOR_REGISTRY
from services.digest_agent import analyze_digest
from services.database import get_supabase_client, seed_admin_if_empty

async def get_or_generate_today_digest(user_id: str, access_token: str) -> dict:
    """Main entry point. Called from GET /api/ai-daily-report/today."""
    client = get_supabase_client()
    today = date.today().isoformat()

    # 1. Claim via PostgreSQL RPC
    result = client.rpc("claim_digest_generation", {"p_date": today}).execute()
    row = result.data[0]

    if not row["claimed"]:
        # Someone else is generating, or already completed
        if row["current_status"] == "completed":
            digest = client.table("daily_digests").select("*").eq("id", row["digest_id"]).single().execute()
            return {"status": "completed", "digest_id": row["digest_id"], "digest": digest.data}
        return {"status": row["current_status"], "digest_id": row["digest_id"]}

    # 2. We won the race — generate
    digest_id = row["digest_id"]
    try:
        # Collect (parallel)
        all_items, source_health = await _run_collectors(client, today)

        # Update status
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
            # ... all other fields
        }).eq("id", digest_id).execute()

        # Cleanup old digests (30 days)
        await _cleanup_old_digests(client)

        # Notify via Telegram
        await _notify_telegram(digest)

        return {"status": "completed", "digest_id": digest_id, "digest": {...}}
    except Exception as e:
        client.table("daily_digests").update({"status": "failed"}).eq("id", digest_id).execute()
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

**6.1: Create report routes** — follow `api/routes/reports.py` pattern:

```python
router = APIRouter(prefix="/api/ai-daily-report", tags=["ai-daily-report"])

@router.get("/today")
async def get_today_digest(user: AuthenticatedUser = Depends(get_current_user)):
    """Main endpoint: check permission → claim/return digest."""
    status = await get_digest_access_status(user.user_id, user.access_token)
    if status not in ("admin", "approved"):
        raise HTTPException(403, detail=f"Access status: {status}")
    return await get_or_generate_today_digest(user.user_id, user.access_token)

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

**6.3: Register routers** in `api/index.py`:
```python
from routes.ai_daily_report import router as ai_daily_report_router
from routes.admin import router as admin_router
from routes.bookmarks import router as bookmarks_router
from routes.feedback import router as feedback_router
app.include_router(ai_daily_report_router)
app.include_router(admin_router)
app.include_router(bookmarks_router)
app.include_router(feedback_router)
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

**7.3: Update useAuth.tsx** — add admin/access flags fetched on auth state change.

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

**8.2: KanbanBoard** — columns by category, cards sorted by importance within each column.

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

### Step 10: Weekly Rollup

- Add `weekly_digests` table or reuse `daily_digests` with `type` field
- Create weekly rollup logic in `digest_service.py` (auto-generated from 7 daily digests)
- Frontend: weekly view option on history page

---

### Step 11: Integration Test + Polish

- Run full E2E: visit `/ai-daily-report` → permission check → generation → kanban display
- Test access request flow end-to-end (all 4 states: no request → pending → approved/rejected)
- Test Realtime: verify all 4 subscriptions work (digest progress, request status, admin notifications, Telegram binding)
- Test shared link flow
- Verify Langfuse traces + cost tracking
- Verify Telegram notifications
- Verify 30-day cleanup
- Run all unit tests: `cd api && uv run python -m pytest -v`
- Update `docs/features.md` and `claude-progress.txt`
- Archive progress: `mv claude-progress.txt docs/archive/claude-progress-ai-daily-report.txt`
- Update `CLAUDE.md` Plans Index: `ai-daily-digest.md` → `Done`

---

## Verification Checklist

1. **Unit tests**: `cd api && uv run python -m pytest tests/ -v` — all pass
2. **Permission flow (4 states)**: no request → "Request Access" → pending → admin approves → user sees digest; also test rejected → re-request
3. **Lazy trigger**: first visit generates, second visit returns cache, concurrent visits don't duplicate
4. **Race condition**: simulate 3 concurrent requests — only 1 generation occurs
5. **Collectors**: each returns data (mock in tests, live in smoke test)
6. **Deduplication**: same news from 2 sources appears as 1 item with attribution
7. **Kanban UI**: columns render, sorted by importance, responsive on mobile
8. **Skeleton loading**: shows progress stages during generation
9. **History**: past 30 days visible, older auto-deleted
10. **Share**: generate link, open in incognito → digest visible without auth
11. **Export**: download as Markdown, content matches display
12. **Bookmarks + Feedback**: save item, vote, persist across sessions
13. **Telegram**: authorized users with linked TG receive notification
14. **Langfuse**: traces for collectors + agent + full pipeline visible
15. **Admin page**: view requests (Realtime: new requests appear live), approve/reject, manage admins
16. **Realtime — Digest progress**: subscribe to `daily_digests` status changes, UI updates without polling
17. **Realtime — Access request**: user sees approval/rejection in real-time without refresh
18. **Realtime — Admin notifications**: new access requests appear on admin page without manual refresh
19. **Realtime — Telegram binding**: Settings page updates instantly when Telegram bot completes binding (replaces 3s polling)

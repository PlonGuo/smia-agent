# SmIA - Social Media Intelligence Agent

> **Live site: [smia-agent.vercel.app](https://smia-agent.vercel.app)**

![SmIA Homepage](docs/images/readme-display/homepage.png)

SmIA is a dual-interface AI intelligence platform that aggregates and analyzes content from multiple social media sources — Reddit, YouTube, and Amazon — in response to natural language queries. It delivers structured trend reports with sentiment analysis, key insights, and interactive data visualizations.

It also generates a **daily AI ecosystem digest** — automatically aggregating research papers, trending repos, blog posts, and social discussions into a categorized, importance-scored kanban board.

Unlike traditional scrapers that merely extract raw data, SmIA **understands** content through AI-powered analysis, filtering out noise and surfacing what actually matters.

---

## What It Does

### On-Demand Analysis

Ask a question like *"What's the sentiment on Plaud Note?"* and SmIA will:

1. **Crawl** Reddit posts, YouTube comments, and Amazon reviews in parallel
2. **Clean** the data — stripping ads, spam, and off-topic noise
3. **Analyze** everything with GPT-4o, producing a structured intelligence report
4. **Visualize** the results with interactive charts, sentiment scores, and source breakdowns

Every analysis is saved to your personal dashboard and can be accessed from both the web app and a Telegram bot.

### AI Daily Digest

Visit the digest page and SmIA will:

1. **Collect** from 4 sources in parallel — arXiv papers, GitHub trending repos, RSS/blog feeds, and Bluesky researcher posts
2. **Categorize** every item into 9 categories (Breakthrough, Research, Tooling, Open Source, Infrastructure, Product, Policy, Safety, Other)
3. **Score** importance (1-5 stars) and write a "why it matters" summary for each item
4. **Deduplicate** the same news covered by multiple sources
5. **Present** everything as a kanban board with an executive summary and trending keywords

One digest is generated per day, shared across authorized users, with a 30-day browsable history.

---

## Interfaces

### Web Application

The primary experience — a full-featured React web app with:

- **Natural language query input** — just describe what you want to know
- **Real-time progress tracking** — watch as SmIA fetches, cleans, and analyzes data
- **Interactive results** — sentiment timeline charts, source distribution pie charts, keyword tags, and expandable discussion threads grouped by platform
- **AI Daily Digest** — kanban board of AI ecosystem updates, shareable via 24hr links, exportable as JSON/CSV
- **Historical dashboard** — browse, search, and filter all past analyses with pagination
- **Dark/light theme** — system-aware with manual toggle and circular reveal animation

![SmIA Dashboard](docs/images/readme-display/dashboard.png)

![SmIA Analyze](docs/images/readme-display/analyze.png)

![SmIA Report Detail](docs/images/readme-display/report-detail.png)

![SmIA Report Charts](docs/images/readme-display/report-detail2.png)

![SmIA Settings](docs/images/readme-display/settings.png)

### Telegram Bot

![SmIA Telegram Bot](docs/images/readme-display/telegram.jpg)

A companion mobile experience for quick analysis on the go:

- `/analyze <topic>` — run a full analysis and get a text summary
- `/digest` — get today's AI daily digest summary
- `/history` — view your recent analyses with links to full web reports
- `/bind <code>` — link your Telegram account to the web platform

Telegram analyses automatically sync to the web dashboard, so you can start an analysis from your phone and review the full charts on desktop later.

---

## Architecture

```
                    Users
           ┌─────────┴─────────┐
      Web Browser         Telegram App
           │                    │
           ▼                    ▼
    ┌──────────────────────────────────┐
    │      Vercel (Edge + Serverless)  │
    │  ┌────────────┐ ┌─────────────┐ │
    │  │React SPA   │ │FastAPI +    │ │
    │  │Chakra UI v3│ │Mangum       │ │
    │  │Recharts    │ │PydanticAI   │ │
    │  └────────────┘ └──────┬──────┘ │
    └────────────────────────┼────────┘
                             │
         ┌───────────┬───────┼───────┬───────────┐
         ▼           ▼       ▼       ▼           ▼
    ┌──────────┐ ┌───────┐ ┌─────┐ ┌─────────┐ ┌────────┐
    │Supabase  │ │OpenAI │ │Lang-│ │arXiv    │ │Bluesky │
    │PostgreSQL│ │GPT-4o │ │fuse │ │GitHub   │ │AT Proto│
    │+ Auth    │ │GPT-4.1│ │     │ │RSS/Blogs│ │        │
    └──────────┘ └───────┘ └─────┘ └─────────┘ └────────┘
```

### Backend (Python)

- **FastAPI** running as Vercel serverless functions via Mangum
- **PydanticAI** agents — on-demand analysis (GPT-4o, 4 tools) and daily digest synthesis (GPT-4.1)
- **Structured outputs** — every analysis produces a validated Pydantic model (`TrendReport` or `DailyDigest`)
- **Two-phase digest pipeline** — Phase 1 collects from 4 sources in parallel, Phase 2 runs LLM categorization/scoring — each phase fits within Vercel's 60s serverless budget
- **4 pluggable collectors** (arXiv, GitHub, RSS, Bluesky) registered via `COLLECTOR_REGISTRY` — adding a new source = one file + one import
- **YARS** for Reddit data (no API key required)
- **YouTube Data API v3** for video metadata and comments
- **Firecrawl** for Amazon review extraction
- **Supabase** for PostgreSQL database with Row Level Security
- **Langfuse** for full LLM observability — traces every tool call, token usage, and cost

### Frontend (TypeScript)

- **React 19** with **Vite** for fast builds
- **Chakra UI v3** component library with custom theme system
- **Recharts** for sentiment timeline and source distribution charts
- **Kanban board** for AI digest with 9-category columns, importance scoring, and responsive mobile tabs
- **Supabase Auth** with JWT — email/password and Google OAuth
- **Real-time subscriptions** for digest status updates (collecting → analyzing → completed)
- Lazy-loaded routes and chart components for optimized bundle size

### Cross-Platform Sync

Both interfaces share the same backend and database. A single `user_id` (from Supabase Auth) links web sessions and Telegram accounts through a binding code system. Reports created from either interface appear in the unified dashboard.

---

## Data Sources

### On-Demand Analysis

| Source | Method | What's Collected |
|--------|--------|-----------------|
| **Reddit** | YARS library (no API key) | Posts, comments, upvotes, subreddit context |
| **YouTube** | YouTube Data API v3 | Video metadata, comment threads, like counts |
| **Amazon** | Firecrawl web scraping | Product reviews, ratings, review text |

Each source has a 45-second timeout. If one source fails, SmIA gracefully degrades and continues with the others.

### AI Daily Digest

| Source | Method | What's Collected |
|--------|--------|-----------------|
| **arXiv** | `arxiv` Python library | cs.AI + cs.LG papers from the last 24 hours |
| **GitHub Trending** | GitHub Search API | New AI/LLM repos sorted by stars |
| **RSS/Blogs** | `feedparser` | OpenAI, Anthropic, DeepMind, HuggingFace, Meta AI blogs + researcher Substacks |
| **Bluesky** | AT Protocol API | Posts from ~20 top AI researchers |

All 4 collectors run in parallel. The digest is generated once per day via lazy trigger (first authorized visit), not a cron job.

---

## Report Structures

### On-Demand Analysis (`TrendReport`)

| Field | Description |
|-------|-------------|
| **Topic** | The main subject analyzed |
| **Sentiment** | Positive / Negative / Neutral with a 0-1 score |
| **Summary** | 2-3 sentence executive overview |
| **Key Insights** | 3-5 bullet points highlighting the most important findings |
| **Top Discussions** | Notable posts/comments from each source with links |
| **Keywords** | 5-10 trending terms extracted from the data |
| **Source Breakdown** | Item count per platform |
| **Charts Data** | Sentiment timeline and source distribution for visualization |
| **Metadata** | Processing time, token usage, Langfuse trace ID |

### AI Daily Digest (`DailyDigest`)

| Field | Description |
|-------|-------------|
| **Executive Summary** | 2-3 sentence overview of the day's AI landscape |
| **Items** | Categorized, importance-scored entries with title, source, author, URL, and "why it matters" |
| **Top Highlights** | 3-5 most significant items of the day |
| **Trending Keywords** | 5-15 tags reflecting the day's themes |
| **Category Counts** | Item distribution across 9 categories |
| **Source Counts** | Item count per collector (arXiv, GitHub, RSS, Bluesky) |
| **Metadata** | Processing time, model used, Langfuse trace ID |

---

## Observability

Every LLM interaction is traced through **Langfuse**:

- Full call chain visibility — from user query to final report
- Per-tool tracing (fetch, clean, analyze)
- Token usage and cost tracking per query
- User and session attribution
- Prompt performance analytics

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, TypeScript |
| UI | Chakra UI v3, Recharts |
| Backend | FastAPI, Python 3.12+ |
| Agent Framework | PydanticAI |
| LLM | OpenAI GPT-4o (analysis), GPT-4.1 (digest) |
| Database | PostgreSQL (Supabase) |
| Auth | Supabase Auth (JWT) |
| Web Scraping | YARS, Firecrawl, YouTube API |
| Digest Sources | arXiv, GitHub API, feedparser, AT Protocol |
| Observability | Langfuse |
| Deployment | Vercel (Edge + Serverless) |
| Package Managers | uv (Python), pnpm (Node.js) |

---

## Project Structure

```
smia-agent/
├── api/                          # FastAPI backend
│   ├── index.py                  # Entrypoint (Mangum handler)
│   ├── routes/
│   │   ├── analyze.py            # POST /api/analyze
│   │   ├── reports.py            # Reports CRUD
│   │   ├── ai_daily_report.py    # AI Digest endpoints
│   │   ├── admin.py              # Admin panel API
│   │   ├── auth.py               # Telegram binding
│   │   └── telegram.py           # Webhook endpoint
│   ├── services/
│   │   ├── agent.py              # PydanticAI agent (on-demand)
│   │   ├── digest_agent.py       # PydanticAI agent (daily digest)
│   │   ├── digest_service.py     # Two-phase digest orchestrator
│   │   ├── collectors/           # Pluggable data collectors
│   │   │   ├── arxiv_collector.py
│   │   │   ├── github_collector.py
│   │   │   ├── rss_collector.py
│   │   │   └── bluesky_collector.py
│   │   ├── tools.py              # Agent tools (fetch, clean)
│   │   ├── crawler.py            # Multi-source crawling
│   │   ├── database.py           # Supabase operations
│   │   └── telegram_service.py   # Bot command handlers
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   ├── core/
│   │   ├── config.py             # Environment config
│   │   ├── auth.py               # JWT verification
│   │   └── langfuse_config.py    # Langfuse setup
│   └── tests/                    # Unit tests
│
├── frontend/                     # React application
│   └── src/
│       ├── pages/                # 11 pages (Home, Login, Signup,
│       │                         #   Analyze, Dashboard, ReportDetail,
│       │                         #   Settings, AiDailyReport,
│       │                         #   AiDailyReportHistory,
│       │                         #   AiDailyReportDetail,
│       │                         #   AiDailyReportShared)
│       ├── components/           # Reusable UI components
│       │   ├── charts/           # Recharts visualizations
│       │   ├── digest/           # AI Digest components
│       │   │   ├── KanbanBoard.tsx
│       │   │   ├── KanbanCard.tsx
│       │   │   ├── DigestHeader.tsx
│       │   │   ├── ShareButton.tsx
│       │   │   └── ExportButton.tsx
│       │   ├── ReportViewer.tsx   # Full report display
│       │   ├── ReportCard.tsx     # Dashboard card
│       │   └── AnalysisForm.tsx   # Query input
│       ├── hooks/
│       │   ├── useAuth.ts        # Authentication hook
│       │   └── useColorMode.ts   # Theme toggle with view transitions
│       └── lib/
│           ├── api.ts            # Typed API client
│           ├── supabase.ts       # Supabase client
│           └── theme.ts          # Chakra UI theme
│
├── shared/                       # Shared TypeScript types
├── libs/yars/                    # Reddit scraping library
├── scripts/                      # Utility scripts
└── vercel.json                   # Deployment config
```

---

## Security

- **Row Level Security** on all database tables — users can only access their own data
- **JWT authentication** on all API endpoints (except the Telegram webhook, which is validated via bot token)
- **Digest access control** — 3-tier permission system (Admin / Approved / Regular) with request-and-approve workflow
- **Shareable digest links** — token-based with 24-hour expiry
- **Internal API security** — digest phase triggers secured by `x-internal-secret` header
- **Input validation** via Pydantic models
- **Rate limiting** — 100 requests/hour (web), 10 analyses/hour (Telegram)
- **No raw HTML stored** — only processed analysis results

---

## License

This project is not open for redistribution. All rights reserved.

# SmIA - Social Media Intelligence Agent

> **Live site: [smia-agent.vercel.app](https://smia-agent.vercel.app)**

![SmIA Homepage](docs/images/readme-display/homepage.png)

SmIA is a dual-interface AI intelligence platform that aggregates and analyzes content from 10+ data sources — Reddit, YouTube, Amazon, Hacker News, Dev.to, Stack Exchange, The Guardian, news RSS feeds, Currents API, and web search — in response to natural language queries. It delivers structured trend reports with sentiment analysis, key insights, and interactive data visualizations.

It also generates **multi-topic daily digests** covering AI, Geopolitics, Climate, and Health — automatically aggregating research papers, trending repos, news articles, and social discussions into categorized, importance-scored kanban boards.

Unlike traditional scrapers that merely extract raw data, SmIA **understands** content through AI-powered analysis, filtering out noise and surfacing what actually matters.

---

## What It Does

### On-Demand Analysis

Ask a question like *"What's the sentiment on Plaud Note?"* and SmIA will:

1. **Select** the most relevant data sources for your query (the LLM picks 2-4 tools from 9 available)
2. **Crawl** data from multiple platforms in parallel — social media, forums, news, and product reviews
3. **Clean** the data — stripping ads, spam, and off-topic noise with LLM-based relevance filtering
4. **Analyze** everything with GPT-4.1, producing a structured intelligence report
5. **Visualize** the results with interactive charts, sentiment scores, and source breakdowns

Every analysis is saved to your personal dashboard and can be accessed from both the web app and a Telegram bot.

### Multi-Topic Daily Digest

Visit the digest page and SmIA will generate topic-specific intelligence briefings:

| Topic | Sources | Categories |
|-------|---------|------------|
| **AI** | arXiv, GitHub, RSS/Blogs, Bluesky | Breakthrough, Research, Tooling, Open Source, Infrastructure, Product, Policy, Safety, Other |
| **Geopolitics** | Guardian, News RSS, Currents, Hacker News | Conflict, Diplomacy, Economy, Technology, Policy, Analysis |
| **Climate** | Guardian, Climate RSS, Currents | Research, Policy, Extreme Weather, Energy, Biodiversity, Activism |
| **Health** | Health RSS, Currents | Research, Policy, Infectious Disease, Mental Health, Nutrition, Technology |

For each topic, SmIA will:

1. **Collect** from topic-specific sources in parallel
2. **Categorize** every item into topic-relevant categories
3. **Score** importance (1-5 stars) and write a "why it matters" summary for each item
4. **Deduplicate** the same news covered by multiple sources
5. **Present** everything as a kanban board with an executive summary and trending keywords

One digest per topic is generated per day, shared across authorized users, with a 30-day browsable history.

---

## Interfaces

### Web Application

The primary experience — a full-featured React web app with:

- **Natural language query input** — just describe what you want to know
- **Real-time progress tracking** — watch as SmIA fetches, cleans, and analyzes data
- **Interactive results** — sentiment timeline charts, source distribution pie charts, keyword tags, and expandable discussion threads grouped by platform
- **Multi-topic AI Digest** — kanban boards with topic switcher, shareable via 24hr links, exportable as JSON/CSV
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
- `/digest_geo` / `/digest_climate` / `/digest_health` — topic-specific digests
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
    ┌────────────┐    ┌──────────────────┐
    │  Vercel    │    │   Fly.io         │
    │  (Static)  │    │   (Backend)      │
    │ React SPA  │───▶│ FastAPI          │
    │ Chakra UI  │    │ PydanticAI       │
    │ Recharts   │    │ uvicorn          │
    └────────────┘    └───────┬──────────┘
                              │
      ┌──────────┬────────────┼────────────┬──────────┐
      ▼          ▼            ▼            ▼          ▼
 ┌──────────┐ ┌───────┐ ┌─────────┐ ┌──────────┐ ┌────────┐
 │Supabase  │ │OpenAI │ │Langfuse │ │10+ Data  │ │Gmail   │
 │PostgreSQL│ │GPT-4.1│ │         │ │Sources   │ │SMTP    │
 │+ Auth    │ │       │ │         │ │          │ │        │
 └──────────┘ └───────┘ └─────────┘ └──────────┘ └────────┘
```

### Backend (Python)

- **FastAPI** running on **Fly.io** (512MB, scale-to-zero)
- **PydanticAI** agents — on-demand analysis (GPT-4.1, 9 tools) and multi-topic daily digest synthesis (GPT-4.1)
- **Structured outputs** — every analysis produces a validated Pydantic model (`TrendReport` or `DailyDigest`)
- **Multi-topic digest pipeline** — 4 topics with topic-specific collectors and category schemas
- **7 pluggable collectors** (arXiv, GitHub, RSS, Bluesky, Guardian, Hacker News, Currents) with parameterized configuration per topic
- **10 crawlers** for on-demand analysis — Reddit (YARS), YouTube, Amazon, Hacker News, Dev.to, Stack Exchange, Guardian, News RSS, Web search (Tavily), Currents
- **LLM-based relevance filtering** (gpt-4.1-nano) to pre-filter noisy data
- **Supabase** for PostgreSQL database with Row Level Security
- **Langfuse** for full LLM observability — traces every tool call, token usage, and cost
- **Automated update emails** — GitHub Actions triggers LLM-summarized changelog emails on deploy

### Frontend (TypeScript)

- **React 19** with **Vite** for fast builds
- **Chakra UI v3** component library with custom theme system
- **Recharts** for sentiment timeline and source distribution charts
- **3D particle sphere** landing page with Three.js
- **Multi-topic kanban board** for digest with topic switcher, dynamic category columns, and responsive mobile tabs
- **Supabase Auth** with JWT — email/password and Google OAuth
- **Real-time subscriptions** for digest status updates (collecting → analyzing → completed)
- **SEO optimized** — meta tags, Open Graph, Twitter Cards, JSON-LD structured data, sitemap
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
| **Hacker News** | HN Official API | Top/new stories, comments, scores |
| **Dev.to** | Dev.to API | Articles, reactions, tags |
| **Stack Exchange** | Stack Exchange API | Questions, answers, vote counts |
| **The Guardian** | Guardian API | News articles, opinion pieces |
| **News RSS** | feedparser + RSS feeds | BBC, Reuters, AP, and more |
| **Web Search** | Tavily API | General web search results |
| **Currents News** | Currents API | Real-time news from 15,000+ sources |

The LLM agent intelligently selects 2-4 tools per query based on topic relevance. Each source has a 45-second timeout with graceful degradation.

### Daily Digest Collectors

| Collector | Method | Topics |
|-----------|--------|--------|
| **arXiv** | `arxiv` Python library | AI |
| **GitHub Trending** | GitHub Search API | AI |
| **RSS/Blogs** | `feedparser` | AI, Climate, Health |
| **Bluesky** | AT Protocol API | AI |
| **The Guardian** | Guardian API | Geopolitics, Climate |
| **Hacker News** | HN Official API | Geopolitics |
| **Currents News** | Currents API | Geopolitics, Climate, Health |

Collectors run in parallel per topic. Each digest is generated once per day via lazy trigger (first authorized visit), not a cron job.

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

### Daily Digest (`DailyDigest`)

| Field | Description |
|-------|-------------|
| **Topic** | AI, Geopolitics, Climate, or Health |
| **Executive Summary** | 2-3 sentence overview of the day's landscape for this topic |
| **Items** | Categorized, importance-scored entries with title, source, author, URL, and "why it matters" |
| **Top Highlights** | Most significant items of the day |
| **Trending Keywords** | 5-15 tags reflecting the day's themes |
| **Category Counts** | Item distribution across topic-specific categories |
| **Source Counts** | Item count per collector |
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
| UI | Chakra UI v3, Recharts, Three.js |
| Backend | FastAPI, Python 3.12+ |
| Agent Framework | PydanticAI |
| LLM | OpenAI GPT-4.1 (configurable via env vars) |
| Database | PostgreSQL (Supabase) |
| Auth | Supabase Auth (JWT) |
| Data Sources | YARS, Firecrawl, YouTube API, Tavily, Guardian API, Currents API, HN API, feedparser, AT Protocol |
| Observability | Langfuse |
| Backend Hosting | Fly.io (scale-to-zero) |
| Frontend Hosting | Vercel (static edge) |
| Package Managers | uv (Python), pnpm (Node.js) |

---

## Project Structure

```
smia-agent/
├── api/                          # FastAPI backend
│   ├── index.py                  # Entrypoint (uvicorn)
│   ├── routes/
│   │   ├── analyze.py            # POST /api/analyze
│   │   ├── reports.py            # Reports CRUD
│   │   ├── ai_daily_report.py    # Multi-topic digest endpoints
│   │   ├── admin.py              # Admin panel API
│   │   ├── auth.py               # Telegram binding
│   │   ├── bookmarks.py          # Report bookmarks
│   │   ├── feedback.py           # User feedback
│   │   ├── internal.py           # Internal webhooks (deploy notifications)
│   │   └── telegram.py           # Webhook endpoint
│   ├── services/
│   │   ├── agent.py              # PydanticAI agent (on-demand, 9 tools)
│   │   ├── digest_agent.py       # PydanticAI agent (daily digest)
│   │   ├── digest_service.py     # Topic-aware digest orchestrator
│   │   ├── collectors/           # Pluggable data collectors
│   │   │   ├── arxiv_collector.py
│   │   │   ├── github_collector.py
│   │   │   ├── rss_collector.py
│   │   │   ├── bluesky_collector.py
│   │   │   ├── guardian_collector.py
│   │   │   ├── hackernews_collector.py
│   │   │   └── currents_collector.py
│   │   ├── tools.py              # Agent tools (9 fetch + clean + filter)
│   │   ├── crawler.py            # 10 crawling backends
│   │   ├── database.py           # Supabase operations
│   │   ├── email_service.py      # Gmail SMTP notifications
│   │   ├── update_summarizer.py  # LLM-powered changelog summarizer
│   │   └── telegram_service.py   # Bot command handlers
│   ├── config/
│   │   └── digest_topics.py      # Topic definitions & collector mappings
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   ├── core/
│   │   ├── config.py             # Environment config
│   │   ├── auth.py               # JWT verification
│   │   └── langfuse_config.py    # Langfuse setup
│   └── tests/                    # Unit & integration tests
│
├── frontend/                     # React application
│   └── src/
│       ├── pages/                # 12 pages (Home, Login, Signup,
│       │                         #   Analyze, Dashboard, ReportDetail,
│       │                         #   Settings, Admin, AiDailyReport,
│       │                         #   AiDailyReportHistory,
│       │                         #   AiDailyReportDetail,
│       │                         #   AiDailyReportShared)
│       ├── components/           # Reusable UI components
│       │   ├── charts/           # Recharts visualizations
│       │   ├── digest/           # Kanban board, cards, sharing
│       │   ├── landing/          # 3D particle sphere, tutorial
│       │   ├── admin/            # Admin panel components
│       │   ├── SEO.tsx           # Dynamic meta tags
│       │   ├── ReportViewer.tsx  # Full report display
│       │   ├── ReportCard.tsx    # Dashboard card
│       │   └── AnalysisForm.tsx  # Query input
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
├── Dockerfile                    # Fly.io backend container
├── fly.toml                      # Fly.io deployment config
├── vercel.json                   # Vercel frontend config
└── scripts/                      # Utility scripts
```

---

## Security

- **Row Level Security** on all database tables — users can only access their own data
- **JWT authentication** on all API endpoints (except the Telegram webhook, which is validated via bot token)
- **Digest access control** — 3-tier permission system (Admin / Approved / Regular) with request-and-approve workflow
- **Shareable digest links** — token-based with 24-hour expiry
- **Internal API security** — deploy webhooks and digest triggers secured by `x-internal-secret` header with HMAC validation
- **Input validation** via Pydantic models
- **Rate limiting** — 100 requests/hour (web), 10 analyses/hour (Telegram), 5 analyses/day (free tier)
- **No raw HTML stored** — only processed analysis results
- **Security headers** — HSTS, X-Frame-Options DENY, CSP via Vercel config

---

## License

This project is not open for redistribution. All rights reserved.

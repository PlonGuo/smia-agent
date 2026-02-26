# SmIA Project Status

> Quick-read overview for new Claude Code sessions. For granular detail see `docs/features.md`.

## Project Summary
SmIA (Social Media Intelligence Agent) — dual-interface AI platform (React web + Telegram bot) for social media trend analysis and daily AI intelligence digests.

## Feature Status

| Feature | Status | Key Files |
|---------|--------|-----------|
| **Backend Foundation** | Done | `api/services/agent.py`, `api/routes/analyze.py`, `api/routes/reports.py` |
| **Crawler Service** | Done | `api/services/crawler.py` (Reddit/YARS, YouTube API, Amazon/Crawl4AI, Firecrawl fallback) |
| **Web Frontend (Core)** | Done | `frontend/src/pages/` (Home, Analyze, Dashboard, ReportDetail, Settings, Login, Signup) |
| **Telegram Bot** | Done | `api/services/telegram_service.py`, `api/routes/telegram.py` |
| **AI Daily Digest — Backend** | Done | `api/services/digest_service.py`, `api/services/digest_agent.py`, `api/routes/ai_daily_report.py` |
| **AI Daily Digest — Collectors** | Done | `api/services/collectors/` (arXiv, GitHub, RSS, Bluesky) |
| **AI Daily Digest — Frontend** | Pending | Steps 7-9 in `docs/plans/2026-02-24-ai-daily-digest.md` |
| **Security Hardening** | Pending | `docs/plans/security-hardening.md` |
| **Observability (Langfuse)** | Partial | Tracing works, dashboards/alerts not configured |
| **Phase 4 Polish** | Partial | See unchecked items in `docs/features.md` Phase 4 |

## Architecture

```
frontend/ (React 19 + Vite + Chakra UI v3)  →  api/ (FastAPI + Mangum on Vercel)
                                                  ├── routes/         (REST endpoints)
                                                  ├── services/       (business logic)
                                                  │   ├── agent.py        (PydanticAI analysis)
                                                  │   ├── digest_agent.py (GPT-4.1 digest LLM)
                                                  │   ├── digest_service.py (two-phase orchestrator)
                                                  │   ├── collectors/     (arXiv, GitHub, RSS, Bluesky)
                                                  │   └── telegram_service.py (bot handlers)
                                                  ├── models/         (Pydantic schemas)
                                                  └── core/           (config, auth, langfuse)
Database: Supabase PostgreSQL (project ref: fueryelktpkkwipwyswu)
Deploy: Vercel serverless (Hobby tier, 60s limit)
```

## Key Architecture Decisions
- **Two-phase digest pipeline**: Collectors (Phase 1) → HTTP trigger → LLM analysis (Phase 2). Each gets own 60s Vercel budget.
- **Lazy trigger**: No cron — first user visit each day generates the digest via PostgreSQL atomic RPC lock.
- **Telegram runs collectors inline**: Vercel BackgroundTasks are unreliable; Telegram handler awaits `run_collectors_phase()` directly.
- **Staleness recovery**: Digests stuck >5 min in collecting/analyzing are auto-reset.

## Test Suite
- **256 tests passing** (`cd api && uv run python -m pytest -v`)
- Coverage: models (25), collectors (22), permissions (13), routes, telegram (57), digest service, etc.

## Active Branches
- `main` — production (deployed to Vercel)
- `feature/ai-daily-digest` — behind main, needs sync if resuming frontend work

## Quick Start for New Sessions
1. Read this file for context
2. Read `claude-progress.txt` for current task state
3. Read the relevant plan in `docs/plans/` if working on a feature
4. Run `cd api && uv run python -m pytest -v` to verify everything passes

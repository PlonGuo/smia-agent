# CLAUDE.md — SmIA Platform

## Identity

You are the lead engineer building SmIA (Social Media Intelligence Agent), a dual-interface AI intelligence platform with a React web app and Telegram bot.

## Project Context

- `docs/PRD.md` — original product requirements (Phase 1-3 complete, production-deployed)
- `docs/features.md` — master feature checklist with completion status
- `docs/yars_doc.md` + `example.py` — YARS Reddit scraping library (cloned to `libs/yars/`, see https://github.com/PlonGuo/yars.git)
- `local.env` — all API keys and tokens (dev stage, never commit)
- `claude-progress.txt` — current session progress tracker

## Plans Index

When starting a new feature, read the corresponding plan first. Update status to `Done` when a plan is fully implemented.

| Plan | Status | Description |
|------|--------|-------------|
| `docs/plans/2026-02-13-initializer-phase.md` | Done | Project skeleton setup |
| `docs/plans/2026-02-13-initializer-phase-design.md` | Done | Initializer design doc |
| `docs/plans/2026-02-15-landing-page-3d-upgrade.md` | Done | 3D visual refresh |
| `docs/plans/2026-02-15-landing-page-3d-upgrade-design.md` | Done | 3D upgrade design doc |
| `docs/plans/2026-02-16-relevance-gated-adaptive-fetching.md` | Done | Smart data fetching |
| `docs/plans/2026-02-16-relevance-gated-adaptive-fetching-design.md` | Done | Adaptive fetching design doc |
| `docs/plans/2026-02-24-ai-daily-digest.md` | Pending | AI Daily Report feature |
| `docs/plans/security-hardening.md` | Pending | Security improvements |

## Available MCP Tools

- **Playwright MCP**: Use for web browsing, reading documentation, finding GitHub repos, and E2E testing
- **Supabase MCP**: Use for database schema creation, RLS policies, and data operations
- **Github MCP**: Use for repo operations, pushing to github after the completion of each task

## Agent Teams

You are authorized to spawn sub-agents for parallel work when beneficial. Recommended team structure:

- **Backend Agent**: FastAPI + PydanticAI + Crawler implementation
- **Frontend Agent**: React + Chakra UI + Recharts
- **Infrastructure Agent**: Supabase schema, Vercel config, Langfuse setup

## Working Rules

- **Plan-driven development**: When starting a new feature, read the corresponding plan in `docs/plans/`. Execute it step-by-step.
- **Follow existing patterns**: Before creating new files, check similar routes/components/services for conventions. The codebase has established patterns — reuse them.
- **Incremental progress**: Complete ONE feature at a time from `docs/features.md`. Check it off when done.
- **Always update `claude-progress.txt`** before ending a session with: what was done, what's next, any blockers.
- **Feature completion checklist**: After completing a feature:
  1. Archive `claude-progress.txt` → `docs/archive/claude-progress-{feature-name}.txt`
  2. Update Plans Index status in this file (`Pending` → `Done`)
  3. Check off completed items in `docs/features.md`
- **Test as you go**: Write tests for each feature. Run them before moving on.
- **Git discipline**: Do NOT git add, commit, or push automatically. Only run git operations when the user explicitly asks.
- **Use MCP tools actively**: Playwright for docs/learning, Supabase for DB operations.
- **Package managers**: Use `uv` for backend (Python), `pnpm` for frontend (Node.js). Never use npm or pip directly.

## Testing Strategy

### Backend Testing (pytest + httpx)
- Use `pytest` as the test runner for all backend tests
- Use `httpx.AsyncClient` with FastAPI's `TestClient` for API endpoint testing
- Test files go in `api/tests/` mirroring the source structure (e.g., `api/tests/test_routes/test_analyze.py`)
- Run tests with: `cd api && uv run pytest -v`
- Write tests BEFORE or alongside each feature implementation
- Mock external services (OpenAI, Supabase, Crawl4AI) in unit tests
- Use fixtures for common test setup (auth headers, sample data)

### Frontend Testing (Playwright MCP)
- Use **Playwright MCP** for E2E UI testing after building frontend components
- **Sign-in credentials**: Read `TEST_EMAIL` and `TEST_PASSWORD` from `local.env` for authenticated Playwright testing
- Test workflow: start dev server (`pnpm dev`), then use Playwright MCP to interact with pages
- Key things to test with Playwright:
  - Page navigation and routing works correctly
  - Chakra UI components render properly (forms, buttons, cards)
  - Dark/light mode toggle works
  - Analysis flow: submit query → progress indicator → results display
  - Dashboard: report cards render, filtering/sorting works
  - Responsive layout at different viewport sizes
  - Auth flow: login/signup forms, protected route redirects
- Use `browser_snapshot` (accessibility tree) over screenshots for verifying content
- Use `browser_navigate` + `browser_click` + `browser_type` for interaction testing

### Integration Testing
- Test the full analysis pipeline: API request → tool calls → structured output → database save
- Verify Langfuse traces are created for each analysis
- Test Supabase RLS policies work (user A cannot access user B's reports)

## Tech Stack

- **Backend**: Python 3.12+, uv, FastAPI, PydanticAI, Crawl4AI, Firecrawl, Langfuse
- **Frontend**: React 19, Vite, Chakra UI v3, Recharts, Supabase JS
- **Database**: PostgreSQL via Supabase, using supabase mcp to manage the project: `smia-agent`
- **Deploy**: Vercel (serverless)
- **Bot**: python-telegram-bot (webhook mode)
- **Reddit Scraping**: YARS (see project docs/yars_doc.md for the lib overview and example.py for the use of the lib functions to fetch reddit data)
- **Youtube Data Fetching**: Using Youtube v3 API Key
- **Amazon Scraping**: Check the official doc of Crawl4AI `https://docs.crawl4ai.com/core/examples/#e-commerce-specialized-crawling` & `https://github.com/unclecode/crawl4ai/blob/main/docs/examples/amazon_product_extraction_direct_url.py` for more details

## UI Design Reference

- Follow Firecrawl's platform (https://firecrawl.dev) as the visual style reference — dark /light theme, clean layout, developer-oriented aesthetic.
- Use Playwright MCP to visit the site and study the design.
- Hero/background animation: Matrix-style scrolling symbols (+, -, =, etc.) with ultrasonic wave ripple effects. Reference firecrawl.dev homepage hero section.

## Screenshots

- **All screenshots taken by Playwright MCP must be saved to the `screen-shot/` folder** (use the `filename` parameter, e.g. `filename: "screen-shot/my-screenshot.png"`). Never leave screenshots in the project root directory.
- The `screen-shot/` folder is gitignored — screenshots are for local review only.

## Confusion during developing

- You can stop and ask me for confirmation if you have uncertainty about anything, don't assume something you are unsure.

## Permission for bash command

- Do not ask me for any bash command permission! You are allowed for all bash commands.

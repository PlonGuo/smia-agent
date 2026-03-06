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
| `docs/plans/2026-02-24-ai-daily-digest.md` | Done | AI Daily Report feature |
| `docs/plans/2026-02-26-dashboard-cold-start-fix.md` | Done | Dashboard SWR cache for cold start perf |
| `docs/plans/security-hardening.md` | Pending | Security improvements |

## Available MCP Tools

- **Playwright MCP**: Use for web browsing, reading documentation, finding GitHub repos, and E2E testing
- **Supabase MCP**: Use for database schema creation, RLS policies, and data operations
- **Github MCP**: Use for repo operations, pushing to github after the completion of each task
- **Vercel MCP**: Use for deployment, logs, environment variables, and Vercel project configuration

## Agent Teams

You are authorized to spawn sub-agents for parallel work when beneficial. Recommended team structure:

- **Backend Agent**: FastAPI + PydanticAI + Crawler implementation
- **Frontend Agent**: React + Chakra UI + Recharts
- **Infrastructure Agent**: Supabase schema, Vercel config, Langfuse setup

## Working Rules

- **Plan-driven development**: When starting a new feature, read the corresponding plan in `docs/plans/`. Execute it step-by-step.
- **Plan documentation**: Whenever plan mode is used to make changes, always write a dated `.md` file in `docs/plans/` recording the context, changes, and results. Then update the Plans Index table in this file with the new plan entry.
- **Follow existing patterns**: Before creating new files, check similar routes/components/services for conventions. The codebase has established patterns — reuse them.
- **Incremental progress**: Complete ONE feature at a time from `docs/features.md`. Check it off when done.
- **Always update `claude-progress.txt`** before ending a session with: what was done, what's next, any blockers.
- **Feature completion checklist**: After completing a feature:
  1. Archive `claude-progress.txt` → `docs/archive/claude-progress-{feature-name}.txt`
  2. Update Plans Index status in this file (`Pending` → `Done`)
  3. Check off completed items in `docs/features.md`
- **Test as you go**: Write tests for each feature. Run them before moving on.
- **Git discipline (plan tasks)**: When executing tasks from `docs/plans/`, auto-commit and push to the corresponding remote branch after completing each todo list item. No user confirmation needed.
- **Git discipline (non-plan tasks)**: For work NOT covered by a plan file, do NOT push automatically. Ask the user for permission before pushing.
- **Git discipline (all commits)**: Always commit ALL changed and untracked files to GitHub. Never leave uncommitted files behind.
- **Use MCP tools actively**: Playwright for docs/learning, Supabase for DB operations.
- **Package managers**: Use `uv` for backend (Python), `pnpm` for frontend (Node.js). Never use npm or pip directly.

## Development Rules

详细规范拆分到独立文件，按需查阅：

| 规则 | 文件 | 简述 |
|------|------|------|
| 测试策略 | `docs/rules/testing.md` | pytest + Playwright + 集成测试规范 |
| Vercel 调试 | `docs/rules/vercel-debugging.md` | serverless 日志和调试规范 |

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

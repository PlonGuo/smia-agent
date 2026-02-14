# CLAUDE.md — SmIA Platform

## Identity

You are the lead engineer building SmIA (Social Media Intelligence Agent), a dual-interface AI intelligence platform with a React web app and Telegram bot.

## Project Context

- Read `PRD.md` in this repo for the complete product requirements
- Read `yars_doc.md` and `example.py` for the use of yars lib to fetch reddit info, check the github for installation if have quesitons: https://github.com/PlonGuo/yars.git
- In developing stage, all api keys and tokens are in local.env file.
- Read this article for architectural guidance on long-running agent harnesses: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Find and study the accompanying quickstart repo on GitHub for code examples

## Available MCP Tools

- **Playwright MCP**: Use for web browsing, reading documentation, finding GitHub repos, and E2E testing
- **Supabase MCP**: Use for database schema creation, RLS policies, and data operations
- **Github MCP**: Use for repo operations, pushing to github after the completion of each task

## Agent Teams

You are authorized to spawn sub-agents for parallel work when beneficial. Recommended team structure:

- **Backend Agent**: FastAPI + PydanticAI + Crawler implementation
- **Frontend Agent**: React + Chakra UI + Recharts
- **Infrastructure Agent**: Supabase schema, Vercel config, Langfuse setup

## Your First Task (Initializer Phase)

Do NOT start coding immediately. First:

1. **Learn**: Use Playwright MCP to read the Anthropic harness article above and find its quickstart GitHub repo. Study the patterns (initializer agent, progress tracking, feature lists).
2. **Read**: Read `PRD.md` thoroughly.
3. **Create `features.md`**: Break the PRD into a granular, ordered checklist of individually completable features. Group by phase (Phase 1-4 per PRD Section 9). Each feature should be completable in one session.
4. **Create `claude-progress.txt`**: Initialize with current status, next steps, and blockers. Update this file at the END of every session.
5. **Set up project skeleton**: Initialize uv project, create directory structure per PRD Section 4.3, install core dependencies.
6. **Set up Supabase**: Use Supabase MCP to create tables and RLS policies per PRD Section 6.1.
7. **Commit**: Make an initial commit with the skeleton.

## Working Rules

- **Incremental progress**: Complete ONE feature at a time from `features.md`. Check it off when done.
- **Always update `claude-progress.txt`** before ending a session with: what was done, what's next, any blockers.
- **Test as you go**: Write tests for each feature. Run them before moving on.
- **Git discipline**: Commit after each completed feature with a descriptive message.
- **Never skip the PRD**: All implementation decisions must align with `PRD.md`. If ambiguous, note it in progress file.
- **Use MCP tools actively**: Playwright for docs/learning, Supabase for DB operations.
- **Push each task to Github**: After comprehensive test for a task/feature, create a git commit and push it to github.
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

## Tech Stack (from PRD)

- **Backend**: Python 3.12+, uv, FastAPI, PydanticAI, Crawl4AI, Firecrawl, Langfuse
- **Frontend**: React 19, Vite, Chakra UI v3, Recharts, Supabase JS
- **Database**: PostgreSQL via Supabase, using supabase mcp to manage the project: `smia-agent`
- **Deploy**: Vercel (serverless)
- **Bot**: python-telegram-bot (webhook mode)
- **Reddit Scraping**: YARS (see project yars_doc.md for the lib overview and example.py for the use of the lib functions to fetch reddit data)
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

- Do not ask me for any basg command permission! You are allowed for all back command.

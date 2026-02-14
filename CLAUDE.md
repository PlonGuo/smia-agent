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

## Tech Stack (from PRD)

- **Backend**: Python 3.12+, uv, FastAPI, PydanticAI, Crawl4AI, Firecrawl, Langfuse
- **Frontend**: React 19, Vite, Chakra UI v3, Recharts, Supabase JS
- **Database**: PostgreSQL via Supabase
- **Deploy**: Vercel (serverless)
- **Bot**: python-telegram-bot (webhook mode)
- **Reddit Scraping**: YARS (see project files for example.py and docs)
- **Youtube Data Fetching**: Using Youtube v3 API Key
- **Amazon Scraping**: Check the official doc of Crawl4AI `https://docs.crawl4ai.com/core/examples/#e-commerce-specialized-crawling` & `https://github.com/unclecode/crawl4ai/blob/main/docs/examples/amazon_product_extraction_direct_url.py` for more details

## Confusion during developing

- You can stop and ask me for confirmation if you have uncertainty about anything, don't assume something you are unsure.

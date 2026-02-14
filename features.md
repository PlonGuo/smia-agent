# SmIA Features Checklist

> Granular, ordered checklist of all features broken down from the PRD.
> Each item is individually completable in one session.
> Check off items as they are completed.

---

## Phase 1: Backend Foundation

### 1.1 Project Setup

- [ ] Initialize uv project with `pyproject.toml` at repo root (Python 3.12+)
- [ ] Create backend directory structure: `api/`, `api/routes/`, `api/services/`, `api/models/`, `api/core/`
- [ ] Create frontend directory structure: `frontend/`, `frontend/src/`, etc. (scaffolding only)
- [ ] Create shared directory: `shared/`
- [ ] Add `.env.example` with all required environment variable placeholders
- [ ] Add `.gitignore` covering Python, Node, `.env`, IDE files, `__pycache__`, etc.
- [ ] Install core backend dependencies (fastapi, mangum, pydantic, pydantic-settings, pydantic-ai, openai, langfuse, crawl4ai, firecrawl-py, python-telegram-bot, supabase, python-dotenv, httpx, yars)
- [ ] Create `api/core/config.py` with environment config using `pydantic-settings` (load all keys from env)
- [ ] Create `api/index.py` FastAPI app entrypoint with Mangum handler
- [ ] Create `vercel.json` with function config and rewrite rules per PRD Section 10.2
- [ ] Verify FastAPI app starts locally with `uvicorn` and returns a health check

### 1.2 Database Setup (Supabase)

- [ ] Create Supabase project (if not already done)
- [ ] Create `user_bindings` table with schema per PRD Section 6.1 (id, user_id, telegram_user_id, bind_code, code_expires_at, bound_at, created_at)
- [ ] Create `analysis_reports` table with full schema per PRD Section 6.1 (all columns including JSONB fields, checks, indexes)
- [ ] Enable Row Level Security (RLS) on `analysis_reports`
- [ ] Create RLS policy: users can only access own reports (`auth.uid() = user_id`)
- [ ] Enable RLS on `user_bindings`
- [ ] Create RLS policy: users can only access own bindings
- [ ] Create all database indexes (user_id, created_at DESC, sentiment, full-text search on query)
- [ ] Create `api/services/database.py` with Supabase client initialization and basic CRUD helpers

### 1.3 Pydantic Models

- [ ] Create `api/models/schemas.py` with `TopDiscussion` model
- [ ] Create `TrendReport` model with all fields per PRD Section 6.2 (topic, sentiment, sentiment_score, summary, key_insights, top_discussions, keywords, source_breakdown, charts_data, metadata)
- [ ] Create `AnalyzeRequest` model with validation (min_length=3, max_length=200)
- [ ] Create `AnalyzeResponse` model
- [ ] Create `ReportsListResponse` model with pagination fields
- [ ] Create `BindCodeResponse` and `BindConfirmRequest` models
- [ ] Write unit tests for model validation (valid/invalid inputs, edge cases)

### 1.4 Crawler Service

- [ ] Create `api/services/crawler.py` with base crawler interface
- [ ] Implement Reddit fetching using YARS library (search_reddit, scrape_post_details) -- see `yars_doc.md` and `example.py`
- [ ] Implement YouTube data fetching using YouTube Data API v3 (search + comment threads)
- [ ] Implement Amazon review scraping using Crawl4AI (see Crawl4AI docs for e-commerce extraction)
- [ ] Add Firecrawl as fallback scraper for when Crawl4AI fails (timeout/error)
- [ ] Add 45-second timeout per source crawl
- [ ] Add error handling: graceful degradation when individual sources fail
- [ ] Write unit tests for crawler service (mock external calls, test timeout handling, test fallback logic)

### 1.5 PydanticAI Agent & Tools

- [ ] Create `api/services/tools.py` with `fetch_reddit_tool` using YARS-based crawler
- [ ] Create `fetch_youtube_tool` using YouTube API-based crawler
- [ ] Create `fetch_amazon_tool` using Crawl4AI-based crawler
- [ ] Create `clean_noise_tool` that uses LLM to filter irrelevant content from raw data
- [ ] Create `api/services/agent.py` with PydanticAI agent configuration (model, system prompt, result_type=TrendReport)
- [ ] Register all tools with the PydanticAI agent
- [ ] Implement parallel tool execution for multi-source fetching
- [ ] Write integration test: run agent with a test query and verify TrendReport output shape
- [ ] Verify structured output validation works (auto-retry on validation failure)

### 1.6 Langfuse Integration

- [ ] Create `api/core/langfuse_config.py` with Langfuse client initialization
- [ ] Add `@observe()` decorator to the main analysis function in `agent.py`
- [ ] Add Langfuse trace metadata (user_id, session_id, source, query_type)
- [ ] Ensure each tool call is traced (fetch_reddit, fetch_youtube, fetch_amazon, clean_noise)
- [ ] Add token usage tracking to analysis results
- [ ] Write test to verify traces appear in Langfuse dashboard (manual verification step)

### 1.7 API Endpoints - Analysis

- [ ] Create `api/routes/analyze.py` with `POST /api/analyze` endpoint
- [ ] Implement Supabase JWT auth dependency in `api/core/dependencies.py` (extract user from Authorization header)
- [ ] Wire analysis endpoint to PydanticAI agent, save result to database
- [ ] Add processing time measurement and store in report
- [ ] Add Langfuse trace_id to saved report
- [ ] Add rate limiting: 100 requests/hour per user (web)
- [ ] Add error handling: 400 (invalid query), 422 (source fetch failure), 429 (rate limit), 500 (analysis failure)
- [ ] Write API tests for `/api/analyze` (mock agent, test auth, test error cases)

### 1.8 API Endpoints - Reports CRUD

- [ ] Create `api/routes/reports.py` with `GET /api/reports` (list with pagination)
- [ ] Implement query params: page, per_page, sentiment, source, from_date, to_date, search (full-text)
- [ ] Implement `GET /api/reports/:id` (single report detail)
- [ ] Implement `DELETE /api/reports/:id` (delete with ownership check)
- [ ] Ensure all endpoints enforce auth and user ownership
- [ ] Write API tests for reports CRUD (list, filter, get, delete, auth, 404 cases)

### 1.9 API Endpoints - Auth & Binding

- [ ] Create `api/routes/auth.py` with `GET /api/bind/code` (generate 6-digit binding code, valid 15 min)
- [ ] Implement `POST /api/bind/confirm` for confirming binding from web side (if needed)
- [ ] Add duplicate binding prevention logic
- [ ] Write tests for binding code generation and validation

### 1.10 Backend Integration Testing

- [ ] Create CLI test script that runs a full analysis pipeline end-to-end
- [ ] Verify multi-source data collection works against live sources
- [ ] Validate TrendReport structured output matches schema
- [ ] Confirm Langfuse traces are recorded correctly
- [ ] Confirm reports are saved to Supabase and retrievable via API
- [ ] Test with at least 2 different queries to ensure consistency

---

## Phase 2: Web Frontend

### 2.1 Frontend Project Setup

- [ ] Initialize Vite + React + TypeScript project in `frontend/`
- [ ] Install dependencies: react, react-dom, react-router-dom, @chakra-ui/react, @emotion/react, @emotion/styled, framer-motion, @supabase/supabase-js, recharts, lucide-react
- [ ] Setup Chakra UI v3 provider in `main.tsx` with custom theme
- [ ] Create `frontend/src/lib/theme.ts` with custom colors (brand palette, sentiment colors) per PRD Section 11.3
- [ ] Setup react-router-dom with routes: `/`, `/login`, `/signup`, `/analyze`, `/dashboard`, `/reports/:id`, `/settings`
- [ ] Create `frontend/src/lib/supabase.ts` with Supabase client initialization
- [ ] Create `frontend/src/lib/api.ts` with typed API client functions (analyze, getReports, getReport, deleteReport, getBindCode)
- [ ] Create `shared/types.ts` with TypeScript interfaces (TrendReport, TopDiscussion, AnalyzeRequest, AnalyzeResponse, etc.) per PRD Section 6.3
- [ ] Verify dev server runs and Chakra UI renders correctly

### 2.2 Authentication

- [ ] Create `frontend/src/hooks/useAuth.ts` hook using Supabase Auth (session, user, signIn, signUp, signOut, loading state)
- [ ] Create Login page (`frontend/src/pages/Login.tsx`) with Chakra UI form (email + password)
- [ ] Create Signup page (`frontend/src/pages/Signup.tsx`) with Chakra UI form (email + password + confirm)
- [ ] Add Google OAuth sign-in button (Supabase Auth provider)
- [ ] Implement protected route wrapper (redirect unauthenticated users to `/login`)
- [ ] Add auth state persistence (auto-refresh JWT tokens)
- [ ] Test full auth flow: signup, login, logout, session persistence, protected routes

### 2.3 Landing Page

- [ ] Create Home page (`frontend/src/pages/Home.tsx`) with hero section
- [ ] Implement Matrix-style scrolling symbols background animation (reference firecrawl.dev hero)
- [ ] Add ultrasonic wave ripple effects overlay
- [ ] Add call-to-action buttons (Sign Up / Try Demo)
- [ ] Add feature highlights section explaining SmIA capabilities
- [ ] Implement dark/light theme support for landing page
- [ ] Make landing page fully responsive (mobile, tablet, desktop)

### 2.4 Analysis Page - Query Input & Progress

- [ ] Create Analyze page (`frontend/src/pages/Analyze.tsx`)
- [ ] Create `AnalysisForm.tsx` component with Chakra Input + submit Button
- [ ] Add input validation (non-empty text, min 3 chars)
- [ ] Implement real-time progress indicator with status messages (Understanding query, Fetching data, Cleaning noise, Analyzing with AI, Complete)
- [ ] Add Chakra Progress bar component during analysis
- [ ] Add error handling with Chakra Toast notifications
- [ ] Add retry button on failure
- [ ] Wire form submission to `POST /api/analyze` via API client

### 2.5 Analysis Page - Results Display

- [ ] Create `ReportViewer.tsx` component with full results layout
- [ ] Display executive summary in Chakra Card
- [ ] Display sentiment score with color-coded Badge (green/red/gray)
- [ ] Display key insights as UnorderedList
- [ ] Display top discussions grouped by source using Chakra Tabs
- [ ] Display keywords as Chakra Tag components
- [ ] Display source breakdown metadata (counts per source)
- [ ] Display processing time and token usage metadata

### 2.6 Charts & Visualizations

- [ ] Create `frontend/src/components/charts/SentimentChart.tsx` using Recharts (sentiment timeline line chart)
- [ ] Create `frontend/src/components/charts/SourceDistribution.tsx` using Recharts (pie chart for source breakdown)
- [ ] Integrate charts into ReportViewer with Chakra theme-aware colors
- [ ] Ensure charts are responsive and work in both light/dark modes
- [ ] Add chart loading states (Chakra Skeleton)

### 2.7 Dashboard (History)

- [ ] Create Dashboard page (`frontend/src/pages/Dashboard.tsx`) with responsive Grid layout
- [ ] Create `ReportCard.tsx` component (Card with hover, Avatar icon by sentiment, timestamp, source badge)
- [ ] Implement filtering: Select for sentiment, RadioGroup for source, date range picker
- [ ] Implement sorting: Menu dropdown (newest/oldest, sentiment)
- [ ] Implement search: Input with search icon (full-text search in query/summary)
- [ ] Implement pagination: Button group (Previous/Next) with page info
- [ ] Add delete action with AlertDialog confirmation
- [ ] Add click-to-view navigation to report detail
- [ ] Handle empty state (no reports yet)

### 2.8 Report Detail Page

- [ ] Create ReportDetail page (`frontend/src/pages/ReportDetail.tsx`)
- [ ] Display full report with all visualizations (charts, insights, discussions)
- [ ] Add expandable sections using Chakra Accordion
- [ ] Add source breakdown using Chakra Tabs
- [ ] Display Stat components for metrics (processing time, token cost, analysis date)
- [ ] Add delete IconButton with confirmation
- [ ] Add share Button (copy link to clipboard)
- [ ] Handle 404 (report not found) with friendly error state

### 2.9 Settings Page

- [ ] Create Settings page (`frontend/src/pages/Settings.tsx`)
- [ ] Display account info: email (read-only), registration date
- [ ] Add theme toggle using Chakra useColorMode
- [ ] Add Telegram binding section: status display, generate code Button, Modal with code display
- [ ] Add unbind Telegram Button with confirmation
- [ ] Add danger zone: delete account with AlertDialog and cascade confirmation
- [ ] Wire all actions to backend API

### 2.10 Frontend Polish & Integration

- [ ] Add app-wide navigation bar/sidebar with links to Analyze, Dashboard, Settings
- [ ] Add user avatar/menu in nav with logout option
- [ ] Implement dark mode toggle in navigation
- [ ] Add responsive design across all pages (Chakra breakpoints)
- [ ] Add Chakra Toast for success/error notifications globally
- [ ] Verify full end-to-end flow: login -> analyze -> view results -> dashboard -> report detail -> settings
- [ ] Fix any integration bugs between frontend and backend

---

## Phase 3: Telegram Bot

### 3.1 Bot Setup

- [ ] Register bot with @BotFather and obtain token (manual step, store in env)
- [ ] Create `api/routes/telegram.py` with `POST /telegram/webhook` endpoint
- [ ] Setup python-telegram-bot in webhook mode (not polling)
- [ ] Implement command parser to route incoming messages to handlers
- [ ] Create `api/services/telegram_service.py` with message formatting helpers
- [ ] Create `scripts/setup_telegram_webhook.py` script to register webhook URL with Telegram API

### 3.2 Bot Commands

- [ ] Implement `/start` command: welcome message + instructions + binding info
- [ ] Implement `/help` command: list all available commands with descriptions
- [ ] Implement `/analyze <topic>` command: extract topic, trigger PydanticAI agent, return formatted summary
- [ ] Format analysis response per PRD Section 5.3 F-08 (topic, sentiment, key insights, sources, web link)
- [ ] Implement `/bind <code>` command: validate code, link telegram_user_id to web user_id, send confirmation
- [ ] Implement `/history` command: query last 5 reports, format as clickable list with web links

### 3.3 Account Binding

- [ ] Implement binding flow: lookup bind_code in user_bindings table, validate not expired (15 min)
- [ ] Link telegram_user_id to user_id in user_bindings table
- [ ] Prevent duplicate bindings (one Telegram account per web account)
- [ ] Send confirmation message to Telegram on successful bind
- [ ] Handle unbound user attempting `/analyze`: send helpful error with link to settings page

### 3.4 Cross-Platform Sync

- [ ] Ensure Telegram analyses are saved with `source='telegram'` in database
- [ ] Verify Telegram reports appear in web dashboard (same user_id)
- [ ] Generate and include web report URL in Telegram response (`https://smia.app/reports/{id}`)
- [ ] Add Langfuse tracing for Telegram bot queries (source="telegram" in metadata)

### 3.5 Bot Error Handling

- [ ] Handle invalid query (no topic provided): send user-friendly error
- [ ] Handle unbound account: send message with link to web settings
- [ ] Handle scraping failures: send partial results notice
- [ ] Implement rate limiting: 10 analyses/hour per Telegram user
- [ ] Handle rate limit exceeded: send friendly message with wait time
- [ ] Handle unexpected errors: send generic error message, log to Langfuse

### 3.6 Telegram Bot Testing

- [ ] Manual test `/start` command
- [ ] Manual test `/analyze` with a real topic
- [ ] Manual test `/bind` flow (generate code on web, bind on Telegram)
- [ ] Manual test `/history` command
- [ ] Verify cross-platform sync (analyze on Telegram, view on web dashboard)
- [ ] Verify Langfuse traces for Telegram queries

---

## Phase 4: Observability & Polish

### 4.1 Langfuse Dashboards & Configuration

- [ ] Setup Langfuse project (cloud or self-hosted Docker per PRD Section 10.4)
- [ ] Configure custom dashboards: daily token usage, cost trends, average processing time
- [ ] Setup cost alerts (notify if daily cost exceeds $10)
- [ ] Implement prompt versioning: track system prompt changes in Langfuse
- [ ] Add per-user token consumption tracking
- [ ] Document trace analysis workflow (how to debug a failed analysis using Langfuse)

### 4.2 UI Polish

- [ ] Add Chakra Skeleton loading states to all pages (analysis, dashboard, report detail)
- [ ] Add empty state illustrations/messages (no reports, no results)
- [ ] Add React error boundaries to catch component-level crashes
- [ ] Run accessibility audit (Chakra built-in a11y, keyboard navigation, screen reader support)
- [ ] Polish animations and transitions (page transitions, loading states, hover effects)
- [ ] Ensure consistent spacing, typography, and color usage across all pages

### 4.3 Performance Optimization

- [ ] Optimize frontend bundle size (Chakra UI tree-shaking, lazy-load routes and chart components)
- [ ] Verify all database indexes are in place and used by queries
- [ ] Test Vercel serverless cold start performance and optimize if needed
- [ ] Verify Langfuse async logging is non-blocking (does not add latency to responses)
- [ ] Add frontend caching for dashboard data (avoid re-fetching on every navigation)
- [ ] Profile and optimize the slowest analysis queries

### 4.4 Documentation

- [ ] Generate API documentation via FastAPI auto-docs (OpenAPI/Swagger at `/docs`)
- [ ] Write user guide: how to use the web app (analyze, dashboard, settings)
- [ ] Write user guide: how to use the Telegram bot (commands, binding)
- [ ] Write Langfuse dashboard guide (how to read traces, debug issues)
- [ ] Create README.md with architecture diagram, setup instructions, tech stack overview

### 4.5 Deployment & Launch Prep

- [ ] Configure all environment variables in Vercel dashboard (database, OpenAI, Langfuse, Telegram, Supabase)
- [ ] Deploy backend to Vercel serverless functions
- [ ] Deploy frontend to Vercel static hosting
- [ ] Setup Telegram webhook pointing to production URL
- [ ] Setup custom domain (if applicable)
- [ ] Run end-to-end smoke test on production (web: signup -> analyze -> dashboard; Telegram: bind -> analyze -> history)
- [ ] Monitor Langfuse for any production issues during first 24 hours
- [ ] Fix any production-only bugs discovered during smoke testing

---

## Summary

| Phase | Items | Description |
|-------|-------|-------------|
| Phase 1 | 10 groups, ~55 items | Backend Foundation: project setup, database, models, crawlers, agent, Langfuse, API endpoints, testing |
| Phase 2 | 10 groups, ~50 items | Web Frontend: setup, auth, landing, analysis, charts, dashboard, report detail, settings, polish |
| Phase 3 | 6 groups, ~25 items | Telegram Bot: setup, commands, binding, cross-platform sync, error handling, testing |
| Phase 4 | 5 groups, ~25 items | Observability & Polish: Langfuse dashboards, UI polish, performance, docs, deployment |
| **Total** | **~155 items** | |

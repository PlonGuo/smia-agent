# SmIA Initializer Phase Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up the complete SmIA project skeleton with backend (FastAPI + uv), frontend (React + Vite + Chakra UI), database schema (Supabase), and tracking files (features.md, claude-progress.txt).

**Architecture:** Monorepo with `api/` (Python backend) and `frontend/` (React SPA). Backend uses uv for package management, FastAPI + Mangum for Vercel serverless. Frontend uses Vite + React 19 + Chakra UI v3. YARS library cloned locally for Reddit scraping. Supabase for PostgreSQL + Auth.

**Tech Stack:** Python 3.12+, uv, FastAPI, PydanticAI, Crawl4AI, Langfuse, React 19, Vite, Chakra UI v3, Recharts, Supabase, Vercel

---

## Task 1: Create `features.md`

**Files:**
- Create: `features.md`

**Step 1: Write features.md**

Create the file with all PRD features broken into granular, individually-completable items grouped by phase. Each item has a checkbox. Reference PRD Section 9 for phasing.

```markdown
# SmIA Feature Checklist

## Phase 1: Backend Foundation

### 1.1 Project Setup
- [ ] Initialize uv project in `api/` with Python 3.12+
- [ ] Install core dependencies (fastapi, mangum, pydantic, pydantic-ai, openai, langfuse, crawl4ai, firecrawl-py, python-telegram-bot, supabase, httpx, python-dotenv)
- [ ] Create directory structure: routes/, services/, models/, core/
- [ ] Create `core/config.py` with environment variable loading (pydantic-settings)
- [ ] Create `api/index.py` with FastAPI app + Mangum handler

### 1.2 Database Setup
- [ ] Create `user_bindings` table in Supabase (per PRD 6.1)
- [ ] Create `analysis_reports` table in Supabase (per PRD 6.1)
- [ ] Enable RLS on both tables
- [ ] Create RLS policies (users can only access own data)
- [ ] Create indexes (user_id, created_at, sentiment, full-text on query)

### 1.3 Pydantic Models
- [ ] Create `models/schemas.py` with TrendReport, TopDiscussion, AnalyzeRequest, AnalyzeResponse, ReportsListResponse

### 1.4 Database Service
- [ ] Create `services/database.py` with Supabase client init
- [ ] Implement `save_report()` function
- [ ] Implement `get_reports()` with pagination + filtering
- [ ] Implement `get_report_by_id()`
- [ ] Implement `delete_report()`

### 1.5 Langfuse Integration
- [ ] Create `core/langfuse_config.py` with Langfuse client setup
- [ ] Add `@observe()` decorator pattern for tracing

### 1.6 Reddit Scraping Tool (YARS)
- [ ] Clone YARS repo locally
- [ ] Create `services/tools.py` with `fetch_reddit_tool` using YARS
- [ ] Test Reddit fetching with sample query

### 1.7 YouTube Data Tool
- [ ] Create `fetch_youtube_tool` in `services/tools.py` using YouTube v3 API
- [ ] Test YouTube comment fetching with sample query

### 1.8 Amazon Scraping Tool
- [ ] Create `fetch_amazon_tool` in `services/tools.py` using Crawl4AI
- [ ] Test Amazon review fetching with sample query

### 1.9 Noise Cleaning Tool
- [ ] Create `clean_noise_tool` in `services/tools.py` (LLM-based filtering)

### 1.10 PydanticAI Agent
- [ ] Create `services/agent.py` with Agent setup (GPT-4o, TrendReport result type, system prompt)
- [ ] Register all tools (fetch_reddit, fetch_youtube, fetch_amazon, clean_noise)
- [ ] Test agent with sample query end-to-end

### 1.11 API Endpoints
- [ ] Create `routes/analyze.py` with POST /api/analyze
- [ ] Create `routes/reports.py` with GET /api/reports, GET /api/reports/:id, DELETE /api/reports/:id
- [ ] Create `core/dependencies.py` with Supabase Auth JWT verification
- [ ] Wire routes into main FastAPI app

### 1.12 Backend Testing
- [ ] CLI test script for analysis pipeline
- [ ] Verify multi-source data collection
- [ ] Validate TrendReport structured output
- [ ] Check Langfuse traces in dashboard

## Phase 2: Web Frontend

### 2.1 Frontend Setup
- [ ] Initialize Vite + React 19 + TypeScript in `frontend/`
- [ ] Install Chakra UI v3, Recharts, Supabase JS, react-router-dom, lucide-react, framer-motion
- [ ] Create Chakra provider with custom theme (`lib/theme.ts`)
- [ ] Create Supabase client (`lib/supabase.ts`)
- [ ] Create API client (`lib/api.ts`)
- [ ] Set up routing in `App.tsx`

### 2.2 Authentication
- [ ] Create `hooks/useAuth.ts` with Supabase Auth hook
- [ ] Create Login/Signup page with Chakra forms
- [ ] Add auth guard for protected routes
- [ ] Test login/signup flow

### 2.3 Landing Page
- [ ] Create `pages/Home.tsx` with hero section
- [ ] Matrix-style scrolling symbols animation (reference firecrawl.dev)
- [ ] Call-to-action buttons

### 2.4 Analysis Page
- [ ] Create `components/AnalysisForm.tsx` (query input + submit)
- [ ] Create progress indicator with status messages
- [ ] Create `components/ReportViewer.tsx` (results display)
- [ ] Create `components/charts/SentimentChart.tsx` (Recharts)
- [ ] Create `components/charts/SourceDistribution.tsx` (Recharts pie)
- [ ] Create `pages/Analyze.tsx` combining form + progress + results
- [ ] Test end-to-end analysis flow

### 2.5 Dashboard
- [ ] Create `components/ReportCard.tsx` (history item card)
- [ ] Create `pages/Dashboard.tsx` with grid layout
- [ ] Add filtering (sentiment, source, date range)
- [ ] Add sorting (newest/oldest, sentiment)
- [ ] Add search (full-text)
- [ ] Add pagination
- [ ] Add delete with confirmation dialog

### 2.6 Report Detail Page
- [ ] Create `pages/ReportDetail.tsx` with full visualizations
- [ ] Expandable sections (Accordion)
- [ ] Source breakdown (Tabs)
- [ ] Metadata stats (processing time, token cost)

### 2.7 Settings Page
- [ ] Create `pages/Settings.tsx`
- [ ] Theme toggle (dark/light mode)
- [ ] Account info display
- [ ] Telegram binding UI (generate code, display, unbind)

### 2.8 Frontend Polish
- [ ] Dark mode support throughout
- [ ] Responsive design (mobile-friendly)
- [ ] Error handling with Toast notifications
- [ ] Loading skeletons

## Phase 3: Telegram Bot

### 3.1 Bot Setup
- [ ] Create `routes/telegram.py` with webhook endpoint
- [ ] Create `services/telegram_service.py` with message formatting
- [ ] Implement command parser

### 3.2 Bot Commands
- [ ] Implement `/start` welcome message
- [ ] Implement `/analyze <topic>` triggering PydanticAI agent
- [ ] Implement `/bind <code>` account linking
- [ ] Implement `/history` last 5 reports
- [ ] Implement `/help` command list

### 3.3 Account Binding
- [ ] Create `routes/auth.py` with GET /api/bind/code and POST /api/bind/confirm
- [ ] Implement binding code generation (6-digit, 15-min expiry)
- [ ] Implement binding verification in Telegram /bind command

### 3.4 Cross-Platform Sync
- [ ] Verify Telegram analyses appear in web dashboard
- [ ] Verify web link generation for full reports

### 3.5 Bot Error Handling
- [ ] Invalid query response
- [ ] Unbound account response
- [ ] Scraping failure partial results
- [ ] Rate limiting response

## Phase 4: Observability & Polish

### 4.1 Langfuse Dashboards
- [ ] Configure custom dashboards
- [ ] Set up cost alerts
- [ ] Document trace analysis workflow

### 4.2 UI Polish
- [ ] Loading skeletons (Chakra)
- [ ] Empty states
- [ ] Error boundaries
- [ ] Accessibility audit

### 4.3 Performance
- [ ] Optimize frontend bundle size
- [ ] Verify database indexes
- [ ] Test serverless cold starts
- [ ] Verify Langfuse async logging

### 4.4 Documentation
- [ ] API documentation (FastAPI auto-generates OpenAPI)
- [ ] README with architecture diagram

### 4.5 Deployment
- [ ] Configure Vercel environment variables
- [ ] Set up Telegram webhook
- [ ] End-to-end production test
```

**Step 2: Commit**

```bash
git add features.md
git commit -m "feat: add features.md with granular PRD breakdown by phase"
```

---

## Task 2: Create `claude-progress.txt`

**Files:**
- Create: `claude-progress.txt`

**Step 1: Write initial progress file**

```
# SmIA Progress Tracker
# Updated: 2026-02-13

## Current Status
- Initializer phase in progress
- Project skeleton being set up
- features.md created with full PRD breakdown

## Completed
- [x] Read PRD.md thoroughly
- [x] Studied Anthropic harness article patterns
- [x] Created features.md with phase-grouped checklist
- [x] Created claude-progress.txt

## In Progress
- [ ] Backend project skeleton (uv + FastAPI)
- [ ] Frontend project skeleton (Vite + React + Chakra)
- [ ] Supabase database setup

## Next Steps
1. Initialize uv project in api/
2. Create backend directory structure and install dependencies
3. Initialize frontend with Vite + React + Chakra UI
4. Create vercel.json and .env.example
5. Set up Supabase tables and RLS policies
6. Commit and push skeleton

## Blockers
- None currently

## Key Decisions
- YARS: git clone (not pip install) per user preference
- Sequential initializer approach chosen
- Features stored as Markdown checklist (not JSON) for readability
```

**Step 2: Commit**

```bash
git add claude-progress.txt
git commit -m "feat: add claude-progress.txt for session tracking"
```

---

## Task 3: Initialize Backend Project (uv + FastAPI)

**Files:**
- Create: `api/pyproject.toml`
- Create: `api/index.py`
- Create: `api/routes/__init__.py`
- Create: `api/routes/analyze.py`
- Create: `api/routes/reports.py`
- Create: `api/routes/telegram.py`
- Create: `api/routes/auth.py`
- Create: `api/services/__init__.py`
- Create: `api/services/crawler.py`
- Create: `api/services/agent.py`
- Create: `api/services/tools.py`
- Create: `api/services/telegram_service.py`
- Create: `api/services/database.py`
- Create: `api/models/__init__.py`
- Create: `api/models/schemas.py`
- Create: `api/core/__init__.py`
- Create: `api/core/config.py`
- Create: `api/core/langfuse_config.py`
- Create: `api/core/dependencies.py`

**Step 1: Initialize uv project**

```bash
cd api
uv init --name smia-api --python 3.12
```

**Step 2: Add core dependencies**

```bash
cd api
uv add fastapi mangum pydantic pydantic-settings pydantic-ai openai langfuse "crawl4ai[all]" firecrawl-py python-telegram-bot supabase httpx python-dotenv yars
```

Note: If `yars` is not on PyPI, clone separately:
```bash
git clone https://github.com/PlonGuo/yars.git /Users/plonguo/Git/smia-agent/libs/yars
cd api
uv add ../libs/yars/src
```

**Step 3: Create directory structure**

```bash
mkdir -p api/routes api/services api/models api/core
touch api/routes/__init__.py api/services/__init__.py api/models/__init__.py api/core/__init__.py
```

**Step 4: Create `api/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # AI Services
    openai_api_key: str = ""
    firecrawl_api_key: str = ""

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://us.cloud.langfuse.com"

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""

    # YouTube
    youtube_api_key: str = ""

    # Rate Limiting
    rate_limit_per_hour: int = 10

    model_config = {"env_file": "local.env", "extra": "ignore"}


settings = Settings()
```

**Step 5: Create `api/index.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

app = FastAPI(title="SmIA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# Vercel serverless handler
handler = Mangum(app, lifespan="off")
```

**Step 6: Create stub route files**

Each route file gets a minimal router placeholder:

`api/routes/analyze.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze")
async def analyze_topic():
    return {"message": "Not implemented yet"}
```

`api/routes/reports.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports")
async def list_reports():
    return {"reports": [], "total": 0, "page": 1, "per_page": 20}


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    return {"message": "Not implemented yet"}


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    return {"message": "Not implemented yet"}
```

`api/routes/telegram.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook():
    return {"ok": True}
```

`api/routes/auth.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/bind/code")
async def generate_bind_code():
    return {"message": "Not implemented yet"}


@router.post("/bind/confirm")
async def confirm_binding():
    return {"message": "Not implemented yet"}
```

**Step 7: Create stub service files**

Each service file gets a docstring placeholder:

`api/services/database.py`:
```python
"""Supabase database operations for SmIA."""
```

`api/services/agent.py`:
```python
"""PydanticAI agent configuration for multi-source analysis."""
```

`api/services/tools.py`:
```python
"""PydanticAI tools: fetch_reddit, fetch_youtube, fetch_amazon, clean_noise."""
```

`api/services/crawler.py`:
```python
"""Web scraping with Crawl4AI (primary) and Firecrawl (fallback)."""
```

`api/services/telegram_service.py`:
```python
"""Telegram bot message formatting and interaction logic."""
```

**Step 8: Create stub model file**

`api/models/schemas.py`:
```python
"""Pydantic models for SmIA API."""

from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class TopDiscussion(BaseModel):
    title: str
    url: str
    source: Literal["reddit", "youtube", "amazon"]
    score: int | None = None
    snippet: str | None = None


class TrendReport(BaseModel):
    topic: str = Field(description="Main topic analyzed")
    sentiment: Literal["Positive", "Negative", "Neutral"]
    sentiment_score: float = Field(ge=0, le=1)
    summary: str = Field(min_length=50, max_length=500)
    key_insights: list[str] = Field(min_length=3, max_length=5)
    top_discussions: list[TopDiscussion] = Field(max_length=15)
    keywords: list[str] = Field(min_length=5, max_length=10)
    source_breakdown: dict[str, int]
    charts_data: dict = Field(default_factory=dict)

    # Metadata
    id: str | None = None
    user_id: str | None = None
    query: str | None = None
    source: Literal["web", "telegram"] | None = None
    processing_time_seconds: int | None = None
    langfuse_trace_id: str | None = None
    token_usage: dict | None = None
    created_at: datetime | None = None


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=3, max_length=200)


class AnalyzeResponse(BaseModel):
    report: TrendReport
    message: str = "Analysis complete"


class ReportsListResponse(BaseModel):
    reports: list[TrendReport]
    total: int
    page: int
    per_page: int
```

**Step 9: Create stub core files**

`api/core/langfuse_config.py`:
```python
"""Langfuse observability setup for SmIA."""
```

`api/core/dependencies.py`:
```python
"""FastAPI dependencies: auth verification, rate limiting."""
```

**Step 10: Wire routes into main app**

Update `api/index.py` to include routers:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from routes.analyze import router as analyze_router
from routes.reports import router as reports_router
from routes.telegram import router as telegram_router
from routes.auth import router as auth_router

app = FastAPI(title="SmIA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(reports_router)
app.include_router(telegram_router)
app.include_router(auth_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# Vercel serverless handler
handler = Mangum(app, lifespan="off")
```

**Step 11: Verify backend structure**

```bash
cd api && find . -type f -name "*.py" | sort
```

Expected:
```
./core/__init__.py
./core/config.py
./core/dependencies.py
./core/langfuse_config.py
./index.py
./models/__init__.py
./models/schemas.py
./routes/__init__.py
./routes/analyze.py
./routes/auth.py
./routes/reports.py
./routes/telegram.py
./services/__init__.py
./services/agent.py
./services/crawler.py
./services/database.py
./services/telegram_service.py
./services/tools.py
```

**Step 12: Commit**

```bash
git add api/
git commit -m "feat: scaffold backend with uv, FastAPI, routes, services, and models"
```

---

## Task 4: Clone YARS Library

**Files:**
- Create: `libs/yars/` (git clone)

**Step 1: Clone YARS**

```bash
mkdir -p libs
git clone https://github.com/PlonGuo/yars.git libs/yars
```

**Step 2: Add libs/yars to .gitignore**

Append to `.gitignore`:
```
libs/
```

**Step 3: Commit .gitignore update**

```bash
git add .gitignore
git commit -m "chore: add libs/ to gitignore for local YARS clone"
```

---

## Task 5: Initialize Frontend Project

**Files:**
- Create: `frontend/` (Vite scaffold)
- Create: `frontend/src/lib/theme.ts`
- Create: `frontend/src/lib/supabase.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/pages/Home.tsx`
- Create: `frontend/src/pages/Analyze.tsx`
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/ReportDetail.tsx`
- Create: `frontend/src/pages/Settings.tsx`
- Create: `frontend/src/components/AnalysisForm.tsx`
- Create: `frontend/src/components/ReportViewer.tsx`
- Create: `frontend/src/components/ReportCard.tsx`
- Create: `frontend/src/components/charts/SentimentChart.tsx`
- Create: `frontend/src/components/charts/SourceDistribution.tsx`

**Step 1: Create Vite project**

```bash
npm create vite@latest frontend -- --template react-ts
```

**Step 2: Install dependencies**

```bash
cd frontend
npm install react@19 react-dom@19 react-router-dom @chakra-ui/react @emotion/react @emotion/styled framer-motion @supabase/supabase-js recharts lucide-react
```

**Step 3: Create directory structure**

```bash
mkdir -p frontend/src/{components/charts,pages,lib,hooks}
```

**Step 4: Create `frontend/src/lib/theme.ts`**

```typescript
import { extendTheme } from '@chakra-ui/react';

const theme = extendTheme({
  colors: {
    brand: {
      50: '#e3f2fd',
      100: '#bbdefb',
      200: '#90caf9',
      300: '#64b5f6',
      400: '#42a5f5',
      500: '#2196f3',
      600: '#1e88e5',
      700: '#1976d2',
      800: '#1565c0',
      900: '#0d47a1',
    },
    sentiment: {
      positive: '#4caf50',
      negative: '#f44336',
      neutral: '#9e9e9e',
    },
  },
  fonts: {
    heading: `'Inter', sans-serif`,
    body: `'Inter', sans-serif`,
  },
  config: {
    initialColorMode: 'light',
    useSystemColorMode: true,
  },
});

export default theme;
```

**Step 5: Create stub page/component files**

Each page gets a minimal placeholder:

`frontend/src/pages/Home.tsx`:
```tsx
export default function Home() {
  return <div>Home - Landing Page</div>;
}
```

`frontend/src/pages/Analyze.tsx`:
```tsx
export default function Analyze() {
  return <div>Analyze - Query Interface</div>;
}
```

`frontend/src/pages/Dashboard.tsx`:
```tsx
export default function Dashboard() {
  return <div>Dashboard - Report History</div>;
}
```

`frontend/src/pages/ReportDetail.tsx`:
```tsx
export default function ReportDetail() {
  return <div>Report Detail</div>;
}
```

`frontend/src/pages/Settings.tsx`:
```tsx
export default function Settings() {
  return <div>Settings</div>;
}
```

`frontend/src/components/AnalysisForm.tsx`:
```tsx
export default function AnalysisForm() {
  return <div>Analysis Form</div>;
}
```

`frontend/src/components/ReportViewer.tsx`:
```tsx
export default function ReportViewer() {
  return <div>Report Viewer</div>;
}
```

`frontend/src/components/ReportCard.tsx`:
```tsx
export default function ReportCard() {
  return <div>Report Card</div>;
}
```

`frontend/src/components/charts/SentimentChart.tsx`:
```tsx
export default function SentimentChart() {
  return <div>Sentiment Chart</div>;
}
```

`frontend/src/components/charts/SourceDistribution.tsx`:
```tsx
export default function SourceDistribution() {
  return <div>Source Distribution</div>;
}
```

**Step 6: Create stub lib files**

`frontend/src/lib/supabase.ts`:
```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

`frontend/src/lib/api.ts`:
```typescript
const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}
```

`frontend/src/hooks/useAuth.ts`:
```typescript
/**
 * Authentication hook using Supabase Auth.
 * To be implemented in Phase 2.
 */
export function useAuth() {
  return { user: null, loading: true };
}
```

**Step 7: Set up App.tsx with routing**

Replace `frontend/src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Analyze from './pages/Analyze';
import Dashboard from './pages/Dashboard';
import ReportDetail from './pages/ReportDetail';
import Settings from './pages/Settings';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/reports/:id" element={<ReportDetail />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

**Step 8: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

**Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with Vite, React 19, Chakra UI, routing, and stub components"
```

---

## Task 6: Create Root Configuration Files

**Files:**
- Create: `vercel.json`
- Create: `.env.example`
- Modify: `.gitignore`

**Step 1: Create `vercel.json`**

```json
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/dist",
  "installCommand": "cd frontend && npm install",
  "functions": {
    "api/index.py": {
      "runtime": "python3.12",
      "maxDuration": 60,
      "memory": 1024
    }
  },
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "/api/index.py"
    },
    {
      "source": "/telegram/:path*",
      "destination": "/api/index.py"
    },
    {
      "source": "/:path*",
      "destination": "/index.html"
    }
  ]
}
```

**Step 2: Create `.env.example`**

```bash
# Database (Supabase)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# AI Services
OPENAI_API_KEY=sk-...
FIRECRAWL_API_KEY=fc-...

# YouTube
YOUTUBE_API_KEY=AIza...

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_URL=https://your-app.vercel.app/telegram/webhook

# Frontend (prefix with VITE_)
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_API_BASE=/api
```

**Step 3: Update `.gitignore`**

```
local.env
.env
libs/
node_modules/
frontend/dist/
__pycache__/
*.pyc
.venv/
.vercel/
```

**Step 4: Create `shared/types.ts`**

```typescript
export type Sentiment = 'Positive' | 'Negative' | 'Neutral';

export interface TopDiscussion {
  title: string;
  url: string;
  source: 'reddit' | 'youtube' | 'amazon';
  score?: number;
  snippet?: string;
}

export interface TrendReport {
  topic: string;
  sentiment: Sentiment;
  sentiment_score: number;
  summary: string;
  key_insights: string[];
  top_discussions: TopDiscussion[];
  keywords: string[];
  source_breakdown: Record<string, number>;
  charts_data: {
    sentiment_timeline?: Array<{ date: string; score: number }>;
    source_distribution?: Array<{ source: string; count: number }>;
  };
  id?: string;
  user_id?: string;
  query?: string;
  source?: 'web' | 'telegram';
  processing_time_seconds?: number;
  langfuse_trace_id?: string;
  token_usage?: {
    prompt: number;
    completion: number;
    total: number;
  };
  created_at?: string;
}

export interface AnalyzeRequest {
  query: string;
}

export interface AnalyzeResponse {
  report: TrendReport;
  message: string;
}
```

**Step 5: Commit**

```bash
git add vercel.json .env.example .gitignore shared/
git commit -m "feat: add Vercel config, env example, shared types, and updated gitignore"
```

---

## Task 7: Set Up Supabase Database

**Files:**
- Create: `supabase/schema.sql` (reference copy)

**Step 1: Create SQL schema file for reference**

```bash
mkdir -p supabase
```

`supabase/schema.sql`:
```sql
-- SmIA Database Schema
-- Run this in Supabase SQL Editor

-- Table: user_bindings
CREATE TABLE public.user_bindings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  telegram_user_id BIGINT UNIQUE NOT NULL,
  bind_code VARCHAR(6),
  code_expires_at TIMESTAMP,
  bound_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, telegram_user_id)
);

CREATE INDEX idx_bindings_telegram_user ON user_bindings(telegram_user_id);
CREATE INDEX idx_bindings_user ON user_bindings(user_id);

-- Table: analysis_reports
CREATE TABLE public.analysis_reports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  query TEXT NOT NULL,
  topic VARCHAR(500),
  sentiment VARCHAR(20) CHECK (sentiment IN ('Positive', 'Negative', 'Neutral')),
  sentiment_score NUMERIC(3, 2) CHECK (sentiment_score >= 0 AND sentiment_score <= 1),
  summary TEXT NOT NULL,
  key_insights JSONB NOT NULL DEFAULT '[]',
  top_discussions JSONB NOT NULL DEFAULT '[]',
  keywords JSONB NOT NULL DEFAULT '[]',
  source_breakdown JSONB NOT NULL DEFAULT '{}',
  charts_data JSONB,
  source VARCHAR(20) CHECK (source IN ('web', 'telegram')) NOT NULL,
  processing_time_seconds INTEGER,
  langfuse_trace_id VARCHAR(255),
  token_usage JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reports_user ON analysis_reports(user_id);
CREATE INDEX idx_reports_created ON analysis_reports(created_at DESC);
CREATE INDEX idx_reports_sentiment ON analysis_reports(sentiment);
CREATE INDEX idx_reports_query ON analysis_reports USING GIN (to_tsvector('english', query));

-- Enable Row Level Security
ALTER TABLE public.user_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_reports ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can manage own bindings"
  ON public.user_bindings
  FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own reports"
  ON public.analysis_reports
  FOR ALL
  USING (auth.uid() = user_id);
```

**Step 2: Execute schema in Supabase**

Use Supabase MCP or SQL Editor to run the schema above against the `smia-agent` project.

**Step 3: Verify tables exist**

Query Supabase to confirm `user_bindings` and `analysis_reports` tables are created with correct columns and RLS enabled.

**Step 4: Commit**

```bash
git add supabase/
git commit -m "feat: add Supabase schema SQL with tables, indexes, and RLS policies"
```

---

## Task 8: Update Progress and Final Commit

**Files:**
- Modify: `claude-progress.txt`

**Step 1: Update progress file**

```
# SmIA Progress Tracker
# Updated: 2026-02-13

## Current Status
- Initializer phase COMPLETE
- Project skeleton fully set up
- Ready to begin Phase 1: Backend Foundation

## Completed
- [x] Read PRD.md thoroughly
- [x] Studied Anthropic harness article patterns
- [x] Created features.md with phase-grouped checklist
- [x] Created claude-progress.txt
- [x] Scaffolded backend (uv + FastAPI + routes/services/models/core)
- [x] Cloned YARS library locally
- [x] Scaffolded frontend (Vite + React 19 + Chakra UI + routing)
- [x] Created Vercel config, .env.example, shared types
- [x] Set up Supabase tables with RLS policies
- [x] Initial commit + push

## Next Steps (Phase 1: Backend Foundation)
1. Implement core/config.py with full env loading
2. Implement models/schemas.py with all Pydantic models
3. Implement services/database.py with Supabase operations
4. Implement services/tools.py with Reddit (YARS), YouTube, Amazon tools
5. Implement services/agent.py with PydanticAI agent
6. Implement routes/analyze.py with full analysis pipeline
7. Test end-to-end analysis

## Blockers
- None
```

**Step 2: Commit and push everything**

```bash
git add claude-progress.txt
git commit -m "chore: update progress - initializer phase complete"
git push origin main
```

---

## Summary

| Task | Description | Files Created |
|------|-------------|---------------|
| 1 | features.md | 1 |
| 2 | claude-progress.txt | 1 |
| 3 | Backend skeleton | ~18 Python files |
| 4 | Clone YARS | libs/yars/ |
| 5 | Frontend skeleton | ~15 TS/TSX files |
| 6 | Root config | 4 files |
| 7 | Supabase schema | 1 SQL file + DB tables |
| 8 | Progress update + push | 1 file update |

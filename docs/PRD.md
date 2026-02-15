# Social Media Intelligence Agent (SmIA)

## Product Requirements Document

| Field            | Detail                |
| ---------------- | --------------------- |
| **Version**      | 2.1                   |
| **Last Updated** | 2026-02-13            |
| **Author**       | Product Team          |
| **Status**       | Ready for Development |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision & Scope](#2-product-vision--scope)
3. [User Flows](#3-user-flows)
4. [Technical Architecture](#4-technical-architecture)
5. [Functional Requirements](#5-functional-requirements)
6. [Data Schema](#6-data-schema)
7. [API Specification](#7-api-specification)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Deployment Strategy](#10-deployment-strategy)
11. [Appendix](#11-appendix)

---

## 1. Executive Summary

### 1.1 Background & Pain Point

Users need to monitor multiple information sources daily (Reddit communities, tech forums, news outlets, social media). Manual browsing is time-consuming and noisy — ads, off-topic comments, and irrelevant content drown out the signal.

### 1.2 Proposed Solution

Build a **dual-interface AI intelligence platform** with:

- **Primary Experience: Web Application** - Complete data visualization and interactive analysis
- **Mobile Experience: Telegram Bot** - Instant text summaries on-the-go

Unlike traditional scrapers that merely extract raw data, SmIA understands content through AI-powered analysis, aggregating information from multiple sources (Reddit, YouTube, Amazon, etc.) in response to natural language queries.

### 1.3 Core Value Proposition

- **Web Interface**: Deep data visualization, historical tracking, trend analysis
- **Telegram Bot**: Quick previews during commute, cross-device synchronization
- **AI-Driven**: Automatic noise filtering, sentiment analysis, key insight extraction across multiple data sources
- **Unified Experience**: Telegram queries automatically sync to web dashboard
- **Observable**: Complete LLM tracing and cost monitoring via Langfuse

### 1.4 Tech Stack Overview

| Layer                 | Technology                               | Deployment                  |
| --------------------- | ---------------------------------------- | --------------------------- |
| **Frontend**          | React 19 + Vite                          | Vercel                      |
| **UI Framework**      | Chakra UI v3                             | -                           |
| **Charts**            | Recharts                                 | -                           |
| **Backend API**       | FastAPI (Python 3.12+)                   | Vercel Serverless Functions |
| **Package Manager**   | uv (Astral)                              | -                           |
| **Agent Framework**   | PydanticAI                               | -                           |
| **LLM Observability** | Langfuse                                 | Self-hosted or Cloud        |
| **Database**          | PostgreSQL                               | Supabase                    |
| **Authentication**    | Supabase Auth                            | Supabase                    |
| **Web Scraping**      | Crawl4AI (primary), Firecrawl (fallback) | -                           |
| **LLM**               | OpenAI GPT-4o                            | -                           |
| **Bot Interface**     | python-telegram-bot (Webhook mode)       | Vercel Serverless           |

---

## 2. Product Vision & Scope

### 2.1 Target Users

- **Tech enthusiasts** monitoring multiple communities
- **Product researchers** tracking product sentiment across platforms
- **Market analysts** gathering competitive intelligence
- **Content creators** understanding audience discussions

### 2.2 Core Features (MVP)

**Web Application:**

- Natural language query interface ("What's the sentiment around Plaud Note?")
- Multi-source aggregation (Reddit, YouTube, Amazon reviews)
- Real-time progress tracking
- Interactive data visualizations (sentiment trends, topic clouds)
- Historical dashboard with search and filtering
- User authentication and profile management

**Telegram Bot:**

- Simple command interface (`/analyze <topic>`)
- Text-based summaries
- Web link generation for full reports
- Account binding with web platform

**Cross-Platform:**

- Unified user authentication
- Automatic data synchronization
- Shared analysis history

**Observability:**

- Complete LLM call tracing via Langfuse
- Token usage and cost monitoring
- Prompt performance analytics
- Tool call debugging

### 2.3 Out of Scope (Post-MVP)

- Multi-language support
- Team collaboration features
- Advanced RAG with vector search
- Scheduled monitoring/alerts (future: Dagster integration)
- Custom data export formats
- Mobile native apps (iOS/Android)
- Real-time streaming analysis

---

## 3. User Flows

### 3.1 Web Application Flow

```
New User Journey:
1. Land on homepage → See demo/explanation
2. Sign up (email/Google) via Supabase Auth
3. Redirected to /analyze page
4. Enter natural language query: "What's the sentiment on Plaud Note?"
5. Real-time progress indicator
   - 🔍 Understanding query...
   - 🕵️ Fetching from Reddit, YouTube, Amazon...
   - 🧹 Cleaning noise...
   - 🧠 Analyzing with AI...
   - ✅ Complete!
6. View interactive results:
   - Executive summary
   - Sentiment analysis (Positive/Negative/Neutral with score)
   - Key insights (3-5 bullets)
   - Top discussions from each source
   - Keywords/trending topics
   - Interactive sentiment timeline chart
   - Source distribution pie chart
7. Report auto-saved to history
8. Navigate to /dashboard to see all past analyses

Returning User Journey:
1. Login → Dashboard
2. Browse historical reports
3. Filter by date/source/sentiment
4. Click report → View full visualization
5. Optionally: Analyze new query
```

### 3.2 Telegram Bot Flow

```
First-Time Setup:
1. User finds bot via @SmiaBot
2. Send /start → Welcome message
3. Receive unique binding code
4. Enter code in web app settings
5. Account linked ✅

Analysis Flow:
1. Send: /analyze Plaud Note reviews
2. Bot responds: "🔍 Analyzing Plaud Note across platforms..."
3. After 30-90s: Text summary + web link

   Example response:
   📊 Analysis Complete!

   Topic: Plaud Note
   Sentiment: Positive 😊 (0.72/1.0)

   💡 Key Insights:
   • Recording quality praised across reviews
   • AI transcription accuracy at ~95%
   • Price point considered high

   🔗 View full report with charts:
   https://smia.app/reports/abc-123

   ⏱️ Analyzed 2 min ago

4. Click link → Opens web app with full visualization
5. History auto-synced to web dashboard
```

### 3.3 Cross-Platform Sync

```
Scenario: User analyzes on Telegram, views on Web

[Telegram]
User sends /analyze <topic>
    ↓
Backend processes (user_id: uuid-abc)
    ↓
Multi-source data collection
    ↓
AI analysis with structured output
    ↓
Saved to database with source="telegram"
    ↓
Returns summary to Telegram

[Later: Web Browser]
User logs in → Dashboard
    ↓
Loads all reports where user_id=uuid-abc
    ↓
Telegram analysis appears in history
    ↓
Click to view full charts/data
```

---

## 4. Technical Architecture

### 4.1 System Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│                   User Clients                        │
│  ┌──────────────────┐      ┌──────────────────┐     │
│  │  Web Browser     │      │  Telegram App    │     │
│  │  (React + Chakra)│      │  (@SmiaBot)      │     │
│  └────────┬─────────┘      └────────┬─────────┘     │
└───────────┼──────────────────────────┼───────────────┘
            │                          │
            │ HTTPS                    │ HTTPS Webhook
            ↓                          ↓
┌───────────────────────────────────────────────────────┐
│              Frontend (Vercel)                        │
│  ┌────────────────────────────────────────────────┐  │
│  │  Static Files (React + Chakra UI v3)           │  │
│  │  - Responsive design with Chakra components    │  │
│  │  - Built-in dark mode support                  │  │
│  │  - Deployed to Vercel Edge Network             │  │
│  └────────────────────────────────────────────────┘  │
└────────────────────────┬──────────────────────────────┘
                         │ REST API Calls
                         ↓
┌───────────────────────────────────────────────────────┐
│       Backend API (Vercel Serverless Functions)       │
│  ┌────────────────────────────────────────────────┐  │
│  │  api/index.py (FastAPI + Mangum)               │  │
│  │                                                 │  │
│  │  Endpoints:                                     │  │
│  │  ├── POST   /api/analyze                       │  │
│  │  ├── GET    /api/reports                       │  │
│  │  ├── GET    /api/reports/:id                   │  │
│  │  ├── DELETE /api/reports/:id                   │  │
│  │  ├── POST   /telegram/webhook                  │  │
│  │  ├── GET    /api/bind/code                     │  │
│  │  └── POST   /api/bind/confirm                  │  │
│  │                                                 │  │
│  │  Core Engine (PydanticAI):                     │  │
│  │  ┌────────────────────────────────────────┐   │  │
│  │  │ Agent with Tools:                      │   │  │
│  │  │ ├── fetch_reddit_tool                  │   │  │
│  │  │ ├── fetch_youtube_tool                 │   │  │
│  │  │ ├── fetch_amazon_tool                  │   │  │
│  │  │ └── clean_noise_tool                   │   │  │
│  │  │                                         │   │  │
│  │  │ Result Type: TrendReport (Pydantic)    │   │  │
│  │  │ - Structured outputs guaranteed        │   │  │
│  │  └────────────────────────────────────────┘   │  │
│  │                                                 │  │
│  │  Services:                                      │  │
│  │  ├── crawler.py (Crawl4AI + Firecrawl)        │  │
│  │  ├── analyzer.py (PydanticAI orchestration)   │  │
│  │  ├── telegram_service.py (Bot logic)          │  │
│  │  └── database.py (Supabase client)            │  │
│  └────────────────────────────────────────────────┘  │
└────────────┬──────────────────┬──────────────────────┘
             │                  │
             │                  │ External APIs
             ↓                  ↓
┌──────────────────┐   ┌─────────────────────────────┐
│  Supabase        │   │  External Services          │
│  ┌────────────┐  │   │  ┌───────────────────────┐ │
│  │PostgreSQL  │  │   │  │ OpenAI API            │ │
│  │            │  │   │  │ (GPT-4o)              │ │
│  │- users     │  │   │  └───────────────────────┘ │
│  │- reports   │  │   │  ┌───────────────────────┐ │
│  │- bindings  │  │   │  │ Langfuse              │ │
│  └────────────┘  │   │  │ (LLM Observability)   │ │
│  ┌────────────┐  │   │  └───────────────────────┘ │
│  │ Auth       │  │   │  ┌───────────────────────┐ │
│  └────────────┘  │   │  │ Crawl4AI              │ │
└──────────────────┘   │  │ (Local scraping)      │ │
                       │  └───────────────────────┘ │
                       │  ┌───────────────────────┐ │
                       │  │ Firecrawl API         │ │
                       │  │ (Fallback scraping)   │ │
                       │  └───────────────────────┘ │
                       └─────────────────────────────┘
```

### 4.2 Data Flow: Multi-Source Analysis

**Web Analysis Request:**

```
1. User submits query: "What's the sentiment on Plaud Note?"
2. Frontend calls POST /api/analyze

3. Backend (PydanticAI Agent):
   a. Parse user intent with LLM
   b. Decide which tools to call (Reddit, YouTube, Amazon)
   c. Tools execute in parallel:
      - fetch_reddit("plaud note") → 30 posts
      - fetch_youtube("plaud note review") → 20 comments
      - fetch_amazon("plaud note") → 15 reviews
   d. For each source:
      - clean_noise_tool removes irrelevant content
   e. LLM analyzes aggregated data
   f. Generate TrendReport (Pydantic, structured output)

4. Langfuse automatically traces:
   - Initial query understanding
   - Each tool call (duration, output size)
   - Noise cleaning prompts
   - Final analysis (tokens, cost)

5. Results saved to Supabase PostgreSQL

6. Response returned to frontend

7. Chakra UI components render charts

[All LLM interactions logged to Langfuse for debugging]
```

**Telegram Analysis Request:**

```
1. User sends /analyze <topic> to Telegram
2. Telegram servers POST to /telegram/webhook
3. Extract telegram_user_id, lookup web user_id
4. Same PydanticAI pipeline as web (steps 3-5 above)
5. Generate text summary (no charts)
6. Send message back to Telegram via Bot API
7. Include web link: https://smia.app/reports/{id}
```

### 4.3 Project Structure

```
smia-platform/
├── frontend/                          # React Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── AnalysisForm.tsx      # Query input (Chakra)
│   │   │   ├── ReportViewer.tsx      # Results display
│   │   │   ├── ReportCard.tsx        # History item
│   │   │   └── charts/
│   │   │       ├── SentimentChart.tsx    # Recharts
│   │   │       └── SourceDistribution.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx              # Landing page
│   │   │   ├── Analyze.tsx           # Main analysis page
│   │   │   ├── Dashboard.tsx         # History dashboard
│   │   │   ├── ReportDetail.tsx      # Single report view
│   │   │   └── Settings.tsx          # Account settings
│   │   ├── lib/
│   │   │   ├── api.ts                # API client functions
│   │   │   ├── supabase.ts           # Supabase client
│   │   │   └── theme.ts              # Chakra UI theme
│   │   ├── hooks/
│   │   │   └── useAuth.ts            # Authentication hook
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── api/                               # FastAPI Backend
│   ├── index.py                      # Main entry (Mangum handler)
│   ├── routes/
│   │   ├── analyze.py                # Analysis endpoints
│   │   ├── reports.py                # CRUD for reports
│   │   ├── telegram.py               # Telegram webhook
│   │   └── auth.py                   # Binding logic
│   ├── services/
│   │   ├── crawler.py                # Web scraping
│   │   ├── agent.py                  # PydanticAI agent setup
│   │   ├── tools.py                  # Agent tools (fetch, clean)
│   │   ├── telegram_service.py       # Bot interactions
│   │   └── database.py               # DB operations
│   ├── models/
│   │   └── schemas.py                # Pydantic models
│   ├── core/
│   │   ├── config.py                 # Environment config
│   │   ├── langfuse_config.py        # Langfuse setup
│   │   └── dependencies.py           # FastAPI dependencies
│   ├── requirements.txt
│   └── pyproject.toml                # uv configuration
│
├── shared/                            # Shared types (optional)
│   └── types.ts                      # TypeScript definitions
│
├── .env.example
├── .gitignore
├── vercel.json                        # Vercel configuration
└── README.md
```

### 4.4 Key Dependencies

**Frontend (`frontend/package.json`):**

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^6.20.0",
    "@chakra-ui/react": "^3.0.0",
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "framer-motion": "^11.0.0",
    "@supabase/supabase-js": "^2.39.0",
    "recharts": "^2.10.0",
    "lucide-react": "^0.300.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0"
  }
}
```

**Backend (`api/requirements.txt`):**

```txt
# Core Framework
fastapi==0.109.0
mangum==0.17.0
pydantic==2.5.0
pydantic-settings==2.1.0

# AI Agent
pydantic-ai==0.0.14
openai>=1.0.0

# Observability
langfuse==2.42.0

# Web Scraping
crawl4ai[all]>=0.4.0
firecrawl-py>=0.0.5

# Telegram Bot
python-telegram-bot>=21.0

# Database
supabase>=2.3.0

# Utilities
python-dotenv>=1.0.0
httpx>=0.27.0
```

---

## 5. Functional Requirements

### 5.1 User Authentication

#### F-01: User Registration & Login

- **Web**: Email/password or Google OAuth via Supabase Auth
- **Access Control**: All features require authentication
- **Session Management**: JWT tokens, auto-refresh
- **Profile**: Email, name, creation date

#### F-02: Telegram Account Binding

- **Flow**:
  1. User clicks "Connect Telegram" in web settings
  2. System generates unique 6-digit code (valid 15 minutes)
  3. User sends `/bind {code}` to Telegram bot
  4. System links `telegram_user_id` to web `user_id`
  5. Confirmation message sent to both interfaces
- **Unbinding**: Option to disconnect in settings
- **Validation**: Prevent duplicate bindings

---

### 5.2 Web Application Features

#### F-03: Analysis Page

- **Query Input**:
  - Chakra UI Input component with placeholder
  - Natural language support: "What's the sentiment on Plaud Note?"
  - Validation: Non-empty text required
- **Real-Time Progress**:
  - Chakra UI Progress component
  - Status messages:
    - 🔍 Understanding your query...
    - 🕵️ Fetching data from Reddit, YouTube, Amazon...
    - 🧹 Cleaning noise and irrelevant content...
    - 🧠 Analyzing with AI...
    - ✅ Complete!
- **Error Handling**:
  - Chakra Toast for user-friendly errors
  - Retry button on failures
- **Results Display** (using Chakra components):
  - `Card` component for sections
  - `Badge` for sentiment indicator
  - `Text` with responsive font sizes
  - Executive summary (2-3 sentences)
  - Sentiment score (0-1) with color coding
  - Key insights (`UnorderedList`)
  - Top discussions grouped by source (`Tabs` component)
  - Interactive Recharts visualizations
  - Keywords as `Tag` components

#### F-04: Dashboard (History)

- **Layout**: Chakra `Grid` responsive layout
- **Report Cards**:
  - `Card` component with hover effects
  - `Avatar` icon based on sentiment
  - Timestamp with `useColorMode` for theming
  - Source badge (Web/Telegram)
- **Filtering**:
  - Chakra `Select` for sentiment filter
  - `RadioGroup` for source filter
  - `RangeDatepicker` for date range (third-party)
- **Sorting**: `Menu` dropdown (newest/oldest, sentiment)
- **Search**: Chakra `Input` with search icon
- **Pagination**: Chakra `Button` group (Previous/Next)
- **Actions**:
  - View detail button
  - Delete with `AlertDialog` confirmation

#### F-05: Report Detail Page

- **URL**: `/reports/:id`
- **Layout**: Full-width Chakra `Container`
- **Content**:
  - All visualizations from analysis
  - Expandable sections using `Accordion`
  - Source breakdown using `Tabs`
- **Metadata**:
  - `Stat` components for metrics
  - Analysis date, processing time, token cost
- **Actions**:
  - `IconButton` for delete
  - `Button` for share (copy link)

#### F-06: Settings Page

- **Theme Toggle**: Chakra `useColorMode` hook
- **Account Info**:
  - `FormControl` for display
  - Email (read-only)
  - Registration date
- **Telegram Binding**:
  - `Box` component showing status
  - `Button` to generate binding code
  - `Modal` to display code
  - `Button` to unbind (with confirmation)
- **Danger Zone**:
  - Delete account with `AlertDialog`

---

### 5.3 Telegram Bot Features

#### F-07: Bot Commands

| Command            | Description                    | Example                       |
| ------------------ | ------------------------------ | ----------------------------- |
| `/start`           | Welcome message + instructions | -                             |
| `/analyze <topic>` | Analyze topic across sources   | `/analyze Plaud Note reviews` |
| `/bind <code>`     | Link Telegram to web account   | `/bind 123456`                |
| `/history`         | Show last 5 analyses           | -                             |
| `/help`            | Command list                   | -                             |

#### F-08: Analysis Response Format

```
📊 Analysis Complete!

🎯 Topic: Plaud Note
😊 Sentiment: Positive (0.72/1.0)

💡 Key Insights:
- Recording quality highly praised
- AI transcription accuracy ~95%
- Price point considered high
- Battery life excellent
- App UX needs improvement

📈 Sources analyzed:
- Reddit: 30 posts
- YouTube: 20 comments
- Amazon: 15 reviews

🔗 View full report with charts:
https://smia.app/reports/abc-123

⏱️ Analyzed 2 minutes ago
```

#### F-09: Error Handling

- **Invalid Query**: "Please provide a topic to analyze (e.g., /analyze Plaud Note)"
- **Unbound Account**: "Please bind your Telegram account first. Visit https://smia.app/settings"
- **Scraping Failed**: "Unable to fetch data from some sources. Partial results available."
- **Rate Limiting**: "You've reached the hourly limit (10 analyses). Try again later."

---

### 5.4 Core Analysis Engine (PydanticAI)

#### F-10: Agent Architecture

```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import Literal

# Result type (Structured Output)
class TrendReport(BaseModel):
    topic: str
    sentiment: Literal["Positive", "Negative", "Neutral"]
    sentiment_score: float  # 0-1
    summary: str
    key_insights: list[str]  # 3-5 items
    top_discussions: list[dict]  # By source
    keywords: list[str]  # 5-10 trending words
    source_breakdown: dict  # {"reddit": 30, "youtube": 20, ...}
    charts_data: dict  # For visualization

# Agent with tools
agent = Agent(
    'openai:gpt-4o',
    result_type=TrendReport,
    system_prompt="""
    You are an expert trend analyst. Analyze the provided data
    from multiple sources (Reddit, YouTube, Amazon) and extract
    actionable insights.

    Focus on:
    1. Overall sentiment and trends
    2. Key discussion points
    3. Common themes across sources
    4. Notable differences between platforms

    Ignore: Ads, spam, off-topic content
    """
)

# Tools
@agent.tool
async def fetch_reddit(ctx: RunContext[str], query: str) -> str:
    """Fetch Reddit discussions about {query}"""
    # Implementation using Crawl4AI
    pass

@agent.tool
async def fetch_youtube(ctx: RunContext[str], query: str) -> str:
    """Fetch YouTube comments about {query}"""
    # Implementation using Crawl4AI
    pass

@agent.tool
async def fetch_amazon(ctx: RunContext[str], query: str) -> str:
    """Fetch Amazon reviews for {query}"""
    # Implementation using Crawl4AI
    pass

@agent.tool
async def clean_noise(ctx: RunContext[str], data: str, source: str) -> str:
    """Remove irrelevant content from {source} data"""
    # LLM call to filter noise
    pass
```

#### F-11: Intelligent Crawler (Crawl4AI)

- **Primary**: Crawl4AI with headless browser
  - JavaScript rendering support
  - Auto-scroll for lazy-loaded content
  - Extract clean Markdown
  - `word_count_threshold=10` to filter noise
  - Custom extractors per platform (Reddit, YouTube, Amazon)
- **Fallback**: Firecrawl cloud API
  - Triggered on Crawl4AI timeout/error
  - Bypass Cloudflare/bot detection
- **Content Extraction**: Preserve structure, links, metadata
- **Timeout**: 45s max per source crawl
- **Parallel Execution**: PydanticAI handles concurrency

#### F-12: Structured Outputs (Pydantic)

- **Guaranteed Format**: PydanticAI uses OpenAI Structured Outputs API
- **Validation**: Automatic via Pydantic models
- **Type Safety**: Python backend → TypeScript frontend
- **Retry Logic**: Auto-retry on validation failures (configurable)
- **No JSON Parsing Errors**: Format guaranteed by API

#### F-13: Langfuse Integration

**Observability Features:**

1. **Automatic Tracing**:

```python
from langfuse.decorators import observe, langfuse_context

@observe()  # Decorator auto-traces
async def analyze_trend(user_query: str) -> TrendReport:
    # PydanticAI agent run
    result = await agent.run(user_query)

    # Langfuse automatically captures:
    # - Initial query
    # - Tool calls (fetch_reddit, fetch_youtube, etc.)
    # - Each tool's input/output/duration
    # - LLM calls for analysis
    # - Token usage per call
    # - Final structured output

    return result.data
```

2. **Manual Annotations**:

```python
langfuse_context.update_current_trace(
    user_id=user_id,
    session_id=session_id,
    metadata={"source": "web", "query_type": "multi_source"}
)
```

3. **Cost Tracking**:
   - Automatic token counting
   - Cost calculation per query
   - Aggregated daily/monthly reports
   - Per-user usage tracking

4. **Prompt Versioning**:
   - Track system prompt changes
   - A/B test different prompts
   - Compare performance metrics

5. **Debug Interface** (Langfuse Dashboard):
   - View full trace tree
   - Inspect each LLM call
   - See tool outputs
   - Filter by user/session/time
   - Export traces for analysis

**Deployment Options:**

- **Cloud**: langfuse.com (free tier: 50k events/month)
- **Self-hosted**: Docker container (recommended for production)

#### F-14: Data Persistence

- **Auto-Save**: All analyses saved to database immediately
- **Fields Stored**:
  - User ID
  - Original query
  - TrendReport (full JSON)
  - Source (web/telegram)
  - Langfuse trace ID (for debugging)
  - Timestamps
- **Retention**: Unlimited (user can delete manually)

---

### 5.5 Cross-Platform Synchronization

#### F-15: Unified User Identity

- **Key**: `user_id` (UUID from Supabase Auth)
- **Telegram Mapping**: `telegram_user_id` → `user_id` via `user_bindings` table
- **Lookup Flow**:
  1. Receive Telegram message
  2. Extract `telegram_user_id`
  3. Query `user_bindings` table
  4. Get associated `user_id`
  5. Save report with this `user_id`

#### F-16: Real-Time Sync

- **No polling needed**: Database is source of truth
- **Web loads reports**: `SELECT * FROM reports WHERE user_id = ?`
- **Telegram reports included**: Distinguished by `source='telegram'`

---

## 6. Data Schema

### 6.1 Database Models (PostgreSQL via Supabase)

#### Table: `users` (managed by Supabase Auth)

```sql
CREATE TABLE auth.users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  encrypted_password VARCHAR(255),
  email_confirmed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Table: `user_bindings`

```sql
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
```

#### Table: `analysis_reports`

```sql
CREATE TABLE public.analysis_reports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

  -- Query
  query TEXT NOT NULL,

  -- Content (JSON from TrendReport)
  topic VARCHAR(500),
  sentiment VARCHAR(20) CHECK (sentiment IN ('Positive', 'Negative', 'Neutral')),
  sentiment_score NUMERIC(3, 2) CHECK (sentiment_score >= 0 AND sentiment_score <= 1),
  summary TEXT NOT NULL,
  key_insights JSONB NOT NULL DEFAULT '[]',
  top_discussions JSONB NOT NULL DEFAULT '[]',
  keywords JSONB NOT NULL DEFAULT '[]',
  source_breakdown JSONB NOT NULL DEFAULT '{}',
  charts_data JSONB,

  -- Metadata
  source VARCHAR(20) CHECK (source IN ('web', 'telegram')) NOT NULL,
  processing_time_seconds INTEGER,
  langfuse_trace_id VARCHAR(255),  -- Link to Langfuse trace
  token_usage JSONB,  -- {prompt: 1000, completion: 500, total: 1500}

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reports_user ON analysis_reports(user_id);
CREATE INDEX idx_reports_created ON analysis_reports(created_at DESC);
CREATE INDEX idx_reports_sentiment ON analysis_reports(sentiment);
CREATE INDEX idx_reports_query ON analysis_reports USING GIN (to_tsvector('english', query));
```

### 6.2 Pydantic Models (Backend)

**Core Report Model:**

```python
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class TopDiscussion(BaseModel):
    title: str
    url: str
    source: Literal["reddit", "youtube", "amazon"]
    score: int | None = None  # Upvotes/likes
    snippet: str | None = None  # Preview text

class TrendReport(BaseModel):
    """AI-generated intelligence report"""

    # Core Analysis
    topic: str = Field(description="Main topic analyzed")
    sentiment: Literal["Positive", "Negative", "Neutral"]
    sentiment_score: float = Field(ge=0, le=1, description="0=very negative, 1=very positive")
    summary: str = Field(min_length=50, max_length=500, description="2-3 sentence overview")

    # Insights
    key_insights: list[str] = Field(min_length=3, max_length=5, description="Bullet points")
    top_discussions: list[TopDiscussion] = Field(max_length=15, description="Top posts/comments")
    keywords: list[str] = Field(min_length=5, max_length=10, description="Trending terms")

    # Source Stats
    source_breakdown: dict[str, int] = Field(description="Items per source")

    # Visualization Data
    charts_data: dict = Field(default_factory=dict, description="Frontend chart data")

    # Metadata (added after generation)
    id: str | None = None
    user_id: str | None = None
    query: str | None = None
    source: Literal["web", "telegram"] | None = None
    processing_time_seconds: int | None = None
    langfuse_trace_id: str | None = None
    token_usage: dict | None = None
    created_at: datetime | None = None

class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=3, max_length=200, description="Natural language query")

class AnalyzeResponse(BaseModel):
    report: TrendReport
    message: str = "Analysis complete"

class ReportsListResponse(BaseModel):
    reports: list[TrendReport]
    total: int
    page: int
    per_page: int
```

### 6.3 TypeScript Types (Frontend)

```typescript
// shared/types.ts
export type Sentiment = 'Positive' | 'Negative' | 'Neutral';

export interface TopDiscussion {
  title: string;
  url: string;
  source: 'reddit' | 'youtube' | 'amazon';
  score?: number;
  snippet?: string;
}

export interface TrendReport {
  // Core Analysis
  topic: string;
  sentiment: Sentiment;
  sentiment_score: number; // 0-1
  summary: string;

  // Insights
  key_insights: string[];
  top_discussions: TopDiscussion[];
  keywords: string[];

  // Source Stats
  source_breakdown: Record<string, number>;

  // Charts
  charts_data: {
    sentiment_timeline?: Array<{ date: string; score: number }>;
    source_distribution?: Array<{ source: string; count: number }>;
  };

  // Metadata
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

---

## 7. API Specification

### 7.1 Authentication

All endpoints except `/telegram/webhook` require authentication via Supabase JWT in `Authorization` header:

```
Authorization: Bearer <supabase_jwt_token>
```

### 7.2 Endpoints

#### **POST /api/analyze**

Analyze a topic across multiple sources.

**Request:**

```json
{
  "query": "What's the sentiment on Plaud Note?"
}
```

**Response (200):**

```json
{
  "report": {
    "id": "abc-123",
    "user_id": "user-uuid",
    "query": "What's the sentiment on Plaud Note?",
    "topic": "Plaud Note",
    "sentiment": "Positive",
    "sentiment_score": 0.72,
    "summary": "Plaud Note receives overwhelmingly positive feedback for recording quality and AI transcription, though price remains a concern.",
    "key_insights": [
      "Recording quality praised across all platforms",
      "AI transcription accuracy reported at ~95%",
      "Price point considered high by many reviewers",
      "Battery life consistently exceeds expectations",
      "App UX cited as needing improvement"
    ],
    "top_discussions": [
      {
        "title": "Plaud Note vs Rewind AI comparison",
        "url": "https://reddit.com/...",
        "source": "reddit",
        "score": 234
      },
      {
        "title": "Honest review after 3 months",
        "url": "https://youtube.com/...",
        "source": "youtube",
        "score": 1200
      }
    ],
    "keywords": ["recording", "transcription", "AI", "price", "battery"],
    "source_breakdown": {
      "reddit": 30,
      "youtube": 20,
      "amazon": 15
    },
    "charts_data": {
      "sentiment_timeline": [
        { "date": "2026-02-01", "score": 0.68 },
        { "date": "2026-02-08", "score": 0.72 }
      ],
      "source_distribution": [
        { "source": "reddit", "count": 30 },
        { "source": "youtube", "count": 20 },
        { "source": "amazon", "count": 15 }
      ]
    },
    "source": "web",
    "processing_time_seconds": 67,
    "langfuse_trace_id": "trace-xyz-789",
    "token_usage": {
      "prompt": 8500,
      "completion": 650,
      "total": 9150
    },
    "created_at": "2026-02-13T10:30:00Z"
  },
  "message": "Analysis complete"
}
```

**Errors:**

- `400`: Invalid query format
- `422`: Unable to fetch data from sources
- `429`: Rate limit exceeded
- `500`: Analysis failed

---

#### **GET /api/reports**

List user's analysis history with filtering/pagination.

**Query Parameters:**

- `page` (int, default: 1)
- `per_page` (int, default: 20, max: 100)
- `sentiment` (string, optional: "Positive" | "Negative" | "Neutral")
- `source` (string, optional: "web" | "telegram")
- `from_date` (ISO datetime, optional)
- `to_date` (ISO datetime, optional)
- `search` (string, optional: full-text search in query/summary)

**Response (200):**

```json
{
  "reports": [
    {
      /* TrendReport object */
    },
    {
      /* ... */
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

---

#### **GET /api/reports/:id**

Get single report details.

**Response (200):**

```json
{
  "report": {
    /* Full TrendReport object */
  }
}
```

**Errors:**

- `404`: Report not found or doesn't belong to user

---

#### **DELETE /api/reports/:id**

Delete a report.

**Response (200):**

```json
{
  "message": "Report deleted successfully"
}
```

**Errors:**

- `404`: Report not found or doesn't belong to user

---

#### **GET /api/bind/code**

Generate a new Telegram binding code.

**Response (200):**

```json
{
  "bind_code": "123456",
  "expires_at": "2026-02-13T10:45:00Z"
}
```

---

#### **POST /telegram/webhook**

Telegram webhook endpoint (no auth required, validated via Telegram token).

**Request (from Telegram):**

```json
{
  "update_id": 123456,
  "message": {
    "message_id": 789,
    "from": {
      "id": 987654321,
      "first_name": "John"
    },
    "chat": {
      "id": 987654321,
      "type": "private"
    },
    "text": "/analyze Plaud Note"
  }
}
```

**Response (200):**

```json
{
  "ok": true
}
```

**Internal Flow:**

1. Extract `telegram_user_id` from `message.from.id`
2. Lookup `user_id` from `user_bindings`
3. Parse command and query
4. If `/analyze`: Run PydanticAI agent, send summary to Telegram
5. If `/bind`: Validate code and create binding
6. If `/history`: Query last 5 reports, format list

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Metric              | Target  | Notes                                      |
| ------------------- | ------- | ------------------------------------------ |
| Web page load       | < 2s    | First contentful paint (Chakra lazy loads) |
| API response (CRUD) | < 500ms | Database queries                           |
| Analysis E2E        | 60-120s | Multi-source scraping bottleneck           |
| Telegram response   | < 5s    | Bot acknowledgment                         |
| Langfuse overhead   | < 50ms  | Per LLM call                               |

**Optimization Strategies:**

- Vercel Edge Network for static assets
- Database indexing on `user_id`, `created_at`
- Chakra UI lazy loading for charts
- Parallel tool execution via PydanticAI
- Langfuse async logging (non-blocking)

### 8.2 Scalability

**Vercel Serverless Limits:**

- Max execution: 60s (Hobby), 300s (Pro)
- Memory: 1024MB
- Concurrent executions: Auto-scaled

**Database (Supabase):**

- Free tier: 500MB, 2GB bandwidth/month
- Upgrade path: Pro ($25/mo) for 8GB

**Langfuse:**

- Cloud free tier: 50k events/month
- Self-hosted: Unlimited

**Expected Load (MVP):**

- 100 users
- 10 analyses/user/month = 1000 total
- ~10k LLM calls/month
- Well within free tiers

### 8.3 Reliability

**Error Handling:**

- All exceptions logged to Langfuse
- Graceful degradation: Source fails → continue with others
- User-facing errors: Chakra Toast notifications
- Automatic retry on transient failures

**Monitoring:**

- Vercel Analytics (built-in)
- Supabase Dashboard (query performance)
- Langfuse Dashboard (LLM performance)
- Optional: Sentry for application errors (post-MVP)

**Uptime Target:** 99.9% (Vercel SLA)

### 8.4 Security

**Authentication:**

- Supabase Auth (industry-standard)
- JWT tokens with expiration
- HTTPS only (enforced by Vercel)

**Authorization:**

- Row Level Security (RLS) in Supabase:

```sql
  CREATE POLICY "Users can only access own reports"
  ON analysis_reports
  FOR ALL
  USING (auth.uid() = user_id);
```

**Rate Limiting:**

- Web: 100 requests/hour per user (API Gateway level)
- Telegram: 10 analyses/hour per user (app logic)
- Tracked in database per user

**Input Validation:**

- Query sanitization (Pydantic validation)
- URL filtering in crawler (block malicious domains)
- SQL injection prevention (Parameterized queries)
- XSS protection (React auto-escapes, Chakra sanitizes)

**Secrets Management:**

- Environment variables in Vercel
- Never commit `.env` to Git
- Rotate API keys quarterly
- Langfuse API key separate from OpenAI

### 8.5 Privacy & Compliance

**Data Storage:**

- User content: Analyzed queries and results only
- No raw scraped HTML stored
- Retention: User-controlled (manual deletion)
- No analytics cookies (respect privacy)

**Telegram:**

- Only store `telegram_user_id` (no phone numbers)
- Users can unbind anytime

**Langfuse Data:**

- Traces contain LLM inputs/outputs
- Self-hosted option for sensitive data
- Automatic PII redaction (configurable)

**GDPR (if applicable):**

- Account deletion: Cascade delete all reports
- Data export: JSON endpoint (post-MVP)
- Right to be forgotten: Delete from Langfuse too

### 8.6 Observability (Langfuse)

**Key Metrics Tracked:**

1. **Per-Query Metrics**:
   - Total processing time
   - Token usage (prompt + completion)
   - Cost per query
   - Number of tool calls
   - Success/failure rate

2. **Aggregated Metrics**:
   - Daily/monthly token usage
   - Cost trends
   - Average processing time
   - Most expensive queries
   - Error rates by type

3. **Prompt Analytics**:
   - System prompt versions
   - Tool call success rates
   - Structured output validation failures

4. **User Analytics**:
   - Per-user token consumption
   - Power users identification
   - Cost attribution

**Dashboards:**

- Langfuse web UI (cloud or self-hosted)
- Custom Grafana dashboards (optional)
- Slack/email alerts on anomalies

---

## 9. Implementation Roadmap

### Phase 1: Backend Foundation (Week 1-2)

**Goals:**

- Core API functional
- Database schema deployed
- PydanticAI agent working
- Langfuse integration complete

**Tasks:**

1. **Setup**
   - Initialize project with `uv`
   - Configure Vercel project
   - Create Supabase project, setup database
   - Setup Langfuse (cloud or Docker)

2. **Core Services**
   - Implement `crawler.py` (Crawl4AI + Firecrawl fallback)
   - Implement `tools.py` (PydanticAI tools for Reddit, YouTube, Amazon)
   - Implement `agent.py` (PydanticAI agent configuration)
   - Write unit tests for critical paths

3. **API Endpoints**
   - `/api/analyze` (PydanticAI integration)
   - `/api/reports` (CRUD)
   - Supabase Auth integration
   - Langfuse decorators on all LLM calls

4. **Testing**
   - CLI testing script for analysis pipeline
   - Verify multi-source data collection
   - Validate structured output (TrendReport)
   - Check Langfuse traces in dashboard

**Deliverable:** Functional API deployed to Vercel (CLI testable), Langfuse tracking working

---

### Phase 2: Web Frontend (Week 2-3)

**Goals:**

- User can analyze topics via web UI
- View results with Chakra UI components
- Interactive charts
- Authentication flow complete

**Tasks:**

1. **Project Setup**
   - Vite + React + TypeScript
   - Install Chakra UI v3
   - Setup Chakra provider with custom theme
   - Setup routing (react-router-dom)

2. **Pages**
   - Landing page (Chakra hero components)
   - Login/Signup (Supabase Auth + Chakra forms)
   - Analysis page (Query input + progress + results)
   - Dashboard (Report grid with Chakra Cards)
   - Settings (Chakra form controls)

3. **Components**
   - `AnalysisForm.tsx` (Chakra Input, Button with loading)
   - `ReportViewer.tsx` (Chakra layout components)
   - `SentimentChart.tsx` (Recharts + Chakra theme)
   - `SourceBreakdown.tsx` (Recharts pie chart)
   - `TopDiscussions.tsx` (Chakra Tabs by source)

4. **Integration**
   - API client (`lib/api.ts`)
   - Error handling + Chakra Toast
   - Dark mode toggle (Chakra useColorMode)
   - Responsive design (Chakra breakpoints)

**Deliverable:** Web app deployed to Vercel, end-to-end flow working

---

### Phase 3: Telegram Bot (Week 3-4)

**Goals:**

- Bot responds to commands
- Account binding functional
- Cross-platform sync working
- Langfuse traces bot interactions

**Tasks:**

1. **Bot Setup**
   - Register bot with @BotFather
   - Setup webhook endpoint (`/telegram/webhook`)
   - Implement command parser

2. **Commands**
   - `/start` - Welcome message
   - `/analyze <topic>` - Trigger PydanticAI agent
   - `/bind <code>` - Account linking
   - `/history` - Last 5 reports

3. **Services**
   - `telegram_service.py` (message formatting)
   - Binding logic (`user_bindings` table)
   - Langfuse tracking for bot queries

4. **Testing**
   - Manual testing via Telegram app
   - Verify reports appear in web dashboard
   - Check Langfuse traces show source="telegram"

**Deliverable:** Fully functional Telegram bot with observability

---

### Phase 4: Observability & Polish (Week 4)

**Goals:**

- Langfuse dashboards configured
- Production-ready
- Documentation complete

**Tasks:**

1. **Langfuse Configuration**
   - Setup custom dashboards
   - Configure cost alerts (>$10/day)
   - Setup prompt versioning
   - Document trace analysis workflow

2. **UI Polish**
   - Chakra loading skeletons
   - Empty states (Chakra placeholders)
   - Error boundaries
   - Accessibility audit (Chakra built-in support)

3. **Performance**
   - Optimize bundle size (Chakra tree-shaking)
   - Add database indexes
   - Test serverless cold starts
   - Verify Langfuse async logging

4. **Documentation**
   - User guide (web + Telegram)
   - API documentation (OpenAPI/Swagger via FastAPI)
   - Langfuse dashboard guide
   - README with architecture diagram

5. **Launch Prep**
   - Environment variables configured
   - Domain setup (if custom)
   - Beta testing with 5-10 users
   - Monitor Langfuse for issues

**Deliverable:** Production launch 🚀

---

## 10. Deployment Strategy

### 10.1 Deployment Architecture

```
Production Environment:
├── Frontend
│   └── Vercel (smia-platform.vercel.app)
│       ├── React SPA + Chakra UI (static files)
│       ├── Edge Network (CDN)
│       └── Auto HTTPS
│
├── Backend API
│   └── Vercel Serverless Functions
│       ├── api/index.py (FastAPI + Mangum)
│       ├── PydanticAI agents
│       ├── Auto-scaling
│       └── 60s timeout (Hobby) / 300s (Pro)
│
├── Database
│   └── Supabase
│       ├── PostgreSQL (hosted)
│       ├── Row Level Security enabled
│       └── Automatic backups
│
├── Observability
│   └── Langfuse
│       ├── Option A: Cloud (langfuse.com)
│       └── Option B: Self-hosted (Docker)
│
└── External Services
    ├── OpenAI API (GPT-4o)
    ├── Crawl4AI (local in serverless)
    └── Firecrawl API (cloud)
```

### 10.2 Vercel Configuration

**Root `vercel.json`:**

```json
{
  "buildCommand": "cd frontend && pnpm run build",
  "outputDirectory": "frontend/dist",
  "installCommand": "cd frontend && pnpm install && cd ../api && pip install -r requirements.txt",

  "functions": {
    "api/index.py": {
      "runtime": "python3.9",
      "maxDuration": 60,
      "memory": 1024,
      "includeFiles": "api/**"
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
  ],

  "headers": [
    {
      "source": "/api/:path*",
      "headers": [
        {
          "key": "Access-Control-Allow-Origin",
          "value": "*"
        },
        {
          "key": "Access-Control-Allow-Methods",
          "value": "GET, POST, PUT, DELETE, OPTIONS"
        },
        {
          "key": "Access-Control-Allow-Headers",
          "value": "Content-Type, Authorization"
        }
      ]
    }
  ]
}
```

### 10.3 Environment Variables

**Vercel Environment Variables (set via dashboard or CLI):**

```bash
# Database
DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...  # Backend only

# AI Services
OPENAI_API_KEY=sk-...
FIRECRAWL_API_KEY=fc-...

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com  # Or self-hosted URL

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_URL=https://smia-platform.vercel.app/telegram/webhook

# Security
JWT_SECRET=random-secret-key-here

# Feature Flags
ENABLE_TELEGRAM_BOT=true
RATE_LIMIT_PER_HOUR=10
```

**Local Development (`.env`):**

```bash
# Same as above, but with local values
DATABASE_URL=postgresql://localhost:5432/smia_dev
LANGFUSE_HOST=http://localhost:3000  # If running Langfuse locally
```

### 10.4 Langfuse Deployment

**Option A: Cloud (Recommended for MVP)**

```bash
# 1. Sign up at langfuse.com
# 2. Create project
# 3. Copy API keys to Vercel env vars
# 4. Done! (Free tier: 50k events/month)
```

**Option B: Self-Hosted (Docker)**

```yaml
# docker-compose.yml
version: '3.8'
services:
  langfuse-server:
    image: langfuse/langfuse:latest
    ports:
      - '3000:3000'
    environment:
      DATABASE_URL: postgresql://langfuse:password@db:5432/langfuse
      NEXTAUTH_SECRET: change-me
      NEXTAUTH_URL: http://localhost:3000
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: password
      POSTGRES_DB: langfuse
    volumes:
      - langfuse-data:/var/lib/postgresql/data

volumes:
  langfuse-data:
```

```bash
# Deploy
docker-compose up -d

# Access at http://localhost:3000
# Update LANGFUSE_HOST in Vercel to your domain
```

### 10.5 Deployment Commands

**Initial Setup:**

```bash
# 1. Install Vercel CLI
pnpm i -g vercel

# 2. Link project
vercel link

# 3. Set environment variables (all secrets)
vercel env add DATABASE_URL production
vercel env add OPENAI_API_KEY production
vercel env add LANGFUSE_PUBLIC_KEY production
vercel env add LANGFUSE_SECRET_KEY production
# ... (repeat for all secrets)

# 4. Deploy
vercel --prod
```

**CI/CD (GitHub Integration):**

```
1. Connect GitHub repo to Vercel project
2. Every push to main → auto-deploy to production
3. Pull requests → preview deployments
4. Environment variables inherited from Vercel project
```

**Manual Deploy:**

```bash
# Deploy to production
vercel --prod

# Deploy to preview
vercel
```

### 10.6 Database Migrations

**Supabase Setup:**

```bash
# 1. Create project at supabase.com
# 2. Run SQL in Supabase SQL Editor:

-- Create tables
CREATE TABLE user_bindings (...);
CREATE TABLE analysis_reports (...);

-- Enable RLS
ALTER TABLE analysis_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_own_reports" ON analysis_reports
  FOR ALL USING (auth.uid() = user_id);

-- Create indexes
CREATE INDEX idx_reports_user ON analysis_reports(user_id);
CREATE INDEX idx_reports_created ON analysis_reports(created_at DESC);
CREATE INDEX idx_reports_langfuse ON analysis_reports(langfuse_trace_id);
```

**Migration Strategy (Post-MVP):**

- Use Supabase CLI for version-controlled migrations
- Schema changes: Test in staging → apply to production
- Backward compatibility: No breaking changes to API

### 10.7 Telegram Webhook Setup

**One-time configuration:**

```python
# scripts/setup_telegram_webhook.py
import requests
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")

response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
    json={"url": WEBHOOK_URL}
)

print(response.json())
# Expected: {"ok": true, "result": true, "description": "Webhook was set"}
```

**Run after first deployment:**

```bash
cd api
uv run python scripts/setup_telegram_webhook.py
```

### 10.8 Monitoring & Logging

**Vercel Built-in:**

- Real-time logs in Vercel dashboard
- Function execution metrics
- Error tracking (automatic)

**Supabase:**

- Query performance dashboard
- Database size monitoring
- Connection pooling stats

**Langfuse (Primary Observability):**

- LLM call tracing
- Token usage analytics
- Cost monitoring
- Error tracking
- Prompt performance
- Custom dashboards

**Optional (Post-MVP):**

- Sentry for application errors
- Custom Grafana + Prometheus

### 10.9 Rollback Strategy

**Vercel Deployments:**

- Every deployment has unique URL
- Instant rollback via dashboard:
  1. Go to Deployments tab
  2. Click previous working deployment
  3. Click "Promote to Production"

**Database:**

- Supabase automatic backups (daily)
- Point-in-time recovery (Pro plan)
- Manual backup before major schema changes

**Langfuse:**

- Self-hosted: Backup Postgres database
- Cloud: Automatic backups by Langfuse

### 10.10 Scaling Considerations

**Current Setup (MVP):**

- Serverless auto-scales to demand
- Database: Supabase Free (500MB)
- Langfuse Cloud: Free (50k events/month)
- Estimated capacity: 1000+ users

**Scaling Triggers:**

```
IF monthly_active_users > 1000:
  - Upgrade Supabase to Pro ($25/mo)
  - Enable connection pooling
  - Consider Langfuse Cloud Pro ($69/mo for 1M events)

IF api_requests > 100k/day:
  - Upgrade Vercel to Pro ($20/mo)
  - Add Redis cache (Upstash)

IF langfuse_events > 50k/month:
  - Upgrade Langfuse Cloud or
  - Self-host Langfuse (unlimited)

IF database_size > 8GB:
  - Migrate to dedicated RDS
  - Implement data archival
```

---

## 11. Appendix

### 11.1 Tech Stack Rationale

| Choice            | Reason                                                        |
| ----------------- | ------------------------------------------------------------- |
| **React 19**      | Latest features, industry standard, Chakra UI support         |
| **Chakra UI v3**  | Component library, dark mode, accessibility, fast development |
| **Vite**          | Fast HMR, modern build tool                                   |
| **FastAPI**       | Async support, auto docs, type safety                         |
| **PydanticAI**    | Structured outputs, tool calling, type-safe agent framework   |
| **Langfuse**      | Best-in-class LLM observability, self-hostable                |
| **Vercel**        | Zero-config deployment, excellent DX                          |
| **Supabase**      | Postgres + Auth in one, generous free tier                    |
| **Crawl4AI**      | Open source, headless browser, Python-native                  |
| **OpenAI GPT-4o** | Best-in-class for analysis tasks, structured outputs          |
| **uv**            | 10x faster than pip, modern Python tooling                    |

### 11.2 Alternative Approaches Considered

**Frontend:**

- ❌ shadcn/ui: More customizable but slower development
- ❌ Material-UI: Dated design, heavier bundle
- ✅ Chakra UI v3: Sweet spot of productivity and quality

**Agent Framework:**

- ❌ LangChain: Over-abstracted, debugging difficult
- ❌ LlamaIndex: Focused on RAG, not general agents
- ✅ PydanticAI: Simple, type-safe, structured outputs

**Observability:**

- ❌ LangSmith: Vendor lock-in, expensive
- ❌ Custom logging: Reinventing the wheel
- ✅ Langfuse: Open source, self-hostable, feature-rich

**Backend:**

- ❌ Node.js/Express: Python has better scraping ecosystem
- ❌ Django: Too heavy for API-only backend

**Database:**

- ❌ MongoDB: Relational data (users → reports)
- ❌ Firebase: Vendor lock-in, less SQL flexibility

**Deployment:**

- ❌ AWS Lambda + API Gateway: Manual setup complexity
- ❌ Railway: Great, but Vercel has better frontend integration

### 11.3 Chakra UI Theme Configuration

**Custom Theme (`frontend/src/lib/theme.ts`):**

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
      500: '#2196f3', // Primary
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
  components: {
    Button: {
      defaultProps: {
        colorScheme: 'brand',
      },
    },
    Card: {
      baseStyle: {
        container: {
          borderRadius: 'lg',
          boxShadow: 'md',
        },
      },
    },
  },
  config: {
    initialColorMode: 'light',
    useSystemColorMode: true,
  },
});

export default theme;
```

### 11.4 Langfuse Best Practices

**Trace Organization:**

```python
# Group related operations
@observe(name="multi_source_analysis")
async def analyze_trend(query: str):

    # Sub-operations auto-nested
    @observe(name="fetch_reddit")
    async def fetch_reddit():
        ...

    @observe(name="fetch_youtube")
    async def fetch_youtube():
        ...

    # Langfuse creates hierarchy:
    # multi_source_analysis
    #   ├── fetch_reddit
    #   ├── fetch_youtube
    #   └── analyze_combined
```

**Custom Metadata:**

```python
langfuse_context.update_current_trace(
    user_id=user_id,
    session_id=session_id,
    tags=["multi-source", "reddit", "youtube"],
    metadata={
        "query_length": len(query),
        "sources": ["reddit", "youtube", "amazon"]
    }
)
```

**Cost Alerts:**

```python
# In Langfuse Dashboard:
# 1. Create alert: "Daily cost > $10"
# 2. Send to Slack/Email
# 3. Auto-disable expensive users
```

### 11.5 Future Enhancements (Post-MVP)

**Phase 2 Features:**

1. **Scheduled Monitoring** (Dagster integration)
   - Track topics daily/weekly
   - Email/Telegram alerts on sentiment changes
   - Trend reports generation

2. **Advanced RAG**
   - ChromaDB integration
   - Query previous analyses
   - "Summarize all Plaud discussions this month"

3. **Enhanced Visualizations**
   - Sentiment timeline (multi-day)
   - Topic clustering (word clouds)
   - Comparison mode (Product A vs B)

4. **Team Features**
   - Shared workspaces
   - Collaborative analysis
   - Role-based access

5. **Export & Integrations**
   - PDF report generation
   - Slack integration
   - Notion/Obsidian export
   - Google Sheets export

6. **Langfuse Advanced**
   - Prompt versioning UI
   - A/B test automation
   - Custom evaluation metrics

### 11.6 Known Limitations

**MVP Scope:**

- ❌ No mobile apps (web is responsive via Chakra)
- ❌ No multi-language support (English only)
- ❌ No video/podcast analysis
- ❌ Limited to public URLs (no auth-walled content)
- ❌ No real-time streaming (batch processing only)

**Technical:**

- Serverless cold starts (1-3s delay)
- 60s timeout may fail on very slow sites
- Crawl4AI package size ~200MB (Lambda limits)
- Langfuse async logging may delay slightly

**Mitigations:**

- Cold start: Vercel Pro reduces latency
- Timeout: Firecrawl fallback handles edge cases
- Package size: Optimize dependencies in future
- Langfuse: Non-blocking, acceptable tradeoff

### 11.7 Success Metrics (Post-Launch)

**User Engagement:**

- Daily Active Users (DAU)
- Analyses per user per week
- Telegram vs Web usage ratio
- Return rate (Week 1 → Week 4)

**Technical:**

- Average analysis time
- Crawler success rate (target: >90%)
- API error rate (target: <1%)
- Langfuse trace completion rate (>99%)

**Cost Metrics:**

- Average cost per analysis
- Token usage trends
- Most expensive query types
- Cost per active user

**Quality Metrics:**

- Structured output validation success (>99%)
- User-reported accuracy (survey)
- Sentiment classification confidence scores

### 11.8 Open Questions

1. **Should we support private communities?**
   - Requires authentication to sources
   - Privacy/ToS considerations

2. **Rate limiting strategy?**
   - Free: 10 analyses/day
   - Paid: 100 analyses/day?
   - Dynamic based on cost?

3. **Data retention policy?**
   - Delete after 90 days?
   - Or user-controlled only?

4. **Langfuse data retention?**
   - Keep traces forever?
   - Archive after 30 days?

**Decision:** Address during beta testing with real users

---

## 12. Glossary

| Term                   | Definition                                                    |
| ---------------------- | ------------------------------------------------------------- |
| **Serverless**         | Cloud execution model where provider manages servers          |
| **ASGI**               | Asynchronous Server Gateway Interface (Python standard)       |
| **Mangum**             | Adapter to run ASGI apps (FastAPI) in AWS Lambda/Vercel       |
| **RLS**                | Row Level Security (Postgres feature for data access control) |
| **JWT**                | JSON Web Token (authentication standard)                      |
| **Webhook**            | HTTP callback triggered by events (Telegram → our API)        |
| **Cold Start**         | Initial latency when serverless function first runs           |
| **CDN**                | Content Delivery Network (global cache for static files)      |
| **Structured Outputs** | LLM API feature guaranteeing JSON schema compliance           |
| **Tool Calling**       | LLM deciding which functions to execute                       |
| **Observability**      | System's ability to be monitored and debugged                 |
| **Trace**              | Complete record of LLM call chain (Langfuse concept)          |
| **Agent**              | AI system with tools and decision-making capability           |

---

## Document History

| Version | Date       | Changes                                                          | Author       |
| ------- | ---------- | ---------------------------------------------------------------- | ------------ |
| 1.0     | 2026-02-12 | Initial draft (Telegram-only)                                    | Product Team |
| 2.0     | 2026-02-13 | Major revision: Web-first, dual interface                        | Product Team |
| 2.1     | 2026-02-13 | Added: Chakra UI v3, Langfuse, PydanticAI, Multi-source analysis | Product Team |

---

**End of Document**

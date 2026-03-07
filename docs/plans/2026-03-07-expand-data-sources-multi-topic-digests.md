# Plan: Fly.io Migration + Expand Data Sources + Multi-Topic Digests

## Context

SmIA currently runs on Vercel serverless (60s timeout). The backend needs to migrate to Fly.io first to remove timeout constraints, then expand data sources and digest topics.

**Execution order**: Fly.io migration → New features (no 60s worries, simpler digest pipeline)

**Scope decisions**:
- **Fly.io migration first** — removes 60s limit, enables simpler digest pipeline (no 2-phase hack)
- Add Currents API (600/day free) — skip Mediastack for now
- Separate PydanticAI tools per source (showcases intelligent tool selection)
- Use RSSHub public instance URLs in feed configs for broader coverage
- 4 independent digest topics: AI, Geopolitics, Climate, Health
- Each digest triggers on-demand (frontend dropdown or Telegram command)
- Enable Firecrawl `fetch_web` tool for arbitrary URL scraping
- Configurable LLM: GPT-4.1 (default) or DeepSeek, switchable via env var
- No Reddit for programming queries (system prompt guidance)

**Data volume strategy (no timeout worry on Fly.io)**:
- Per-item truncation: body ≤400 chars, comments top 5 at ≤200 chars each
- Per-tool item cap: max 10-12 items → ~4000-6000 chars per tool
- System prompt: pick 2-4 tools, never all 8 → keeps LLM context manageable
- No timeout pressure — even 90s+ analyze requests are fine

---

## Phase 0: Fly.io Migration

### 0.1. Remove Vercel serverless adapter

**File**: `api/main.py`
- Remove Mangum import and `handler = Mangum(app)` wrapper
- Add uvicorn runner: `if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=8080)`
- Keep all FastAPI routes, middleware, CORS config unchanged

### 0.2. Dockerfile

**File**: `Dockerfile` (new, project root)

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (cache layer)
COPY api/pyproject.toml api/uv.lock* ./api/
COPY libs/ ./libs/

# Install deps
RUN cd api && uv sync --frozen --no-dev

# Copy source
COPY api/ ./api/
COPY shared/ ./shared/
COPY local.env* ./

EXPOSE 8080
CMD ["uv", "run", "--directory", "api", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 0.3. Fly.io config

**File**: `fly.toml` (new, project root)

```toml
app = "smia-agent"
primary_region = "sin"  # Singapore (close to user)

[build]

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"    # Scale to zero when idle
  auto_start_machines = true     # Wake on request
  min_machines_running = 0

[[vm]]
  memory = "256mb"
  cpu_kind = "shared"
  cpus = 1

[checks]
  [checks.health]
    port = 8080
    type = "http"
    interval = "30s"
    timeout = "5s"
    path = "/api/health"
```

### 0.4. Health check endpoint

**File**: `api/routes/health.py` (new, or add to existing main.py)
- `GET /api/health` → `{"status": "ok"}`

### 0.5. Deploy steps (manual)

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login & create app
fly auth login
fly launch --name smia-agent --region sin --no-deploy

# Set secrets (from local.env)
fly secrets set SUPABASE_URL=... SUPABASE_ANON_KEY=... OPENAI_API_KEY=... (etc)

# Deploy
fly deploy

# Verify
fly status
curl https://smia-agent.fly.dev/api/health
```

### 0.6. Update frontend

**File**: `frontend/.env.production`
- Change `VITE_API_BASE=https://smia-agent.fly.dev/api` (or custom domain)

### 0.7. Update Telegram webhook

```bash
curl "https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://smia-agent.fly.dev/api/telegram/webhook&secret_token={SECRET}"
```

### 0.8. Remove Vercel backend config

**File**: `vercel.json`
- Remove `api/` route rewrites (keep frontend-only config)
- Frontend stays on Vercel, backend on Fly.io

### 0.9. Simplify digest pipeline

**File**: `api/services/digest_service.py`
- Remove 2-phase hack: no more HTTP trigger from Phase 1 to Phase 2
- Merge into single function: `run_digest(digest_id)` — collectors → LLM → save, all in one call
- Remove `/api/ai-daily-report/internal/analyze` and `/api/ai-daily-report/internal/collect` internal endpoints
- Remove `INTERNAL_SECRET` dependency for digest pipeline
- Use `asyncio.create_task()` for background execution instead of Vercel BackgroundTask

### 0.10. Verification

1. `curl https://smia-agent.fly.dev/api/health` → 200
2. Frontend can call Fly.io backend (CORS works)
3. Existing analyze works end-to-end
4. Existing AI digest generates successfully
5. Telegram bot responds to commands
6. Run tests locally: `cd api && uv run python -m pytest -v`

---

## Part A: New Analyze Tools

### A1. New crawler functions

**File**: `api/services/crawler.py` (append)

4 new async functions following existing patterns (httpx, timeout, error handling):

**`fetch_hackernews(query, limit=15)`**
- HN Algolia API: `https://hn.algolia.com/api/v1/search?query=...&tags=story&hitsPerPage=N`
- Free, no auth, no rate limit
- Filter by `numericFilters=created_at_i>{unix_timestamp}` for time_range
- For top 5 stories, fetch comments via `https://hn.algolia.com/api/v1/items/{objectID}`
- Return `[{title, url, body, source: "hackernews", comments: [...]}]`

**`fetch_news(query, limit=15)`**
- **Primary**: Parse RSS feeds from `api/config/news_rss_feeds.json` (includes RSSHub URLs)
- Reuse `feedparser` — same pattern as `api/services/collectors/rss_collector.py`
- Filter by keyword match + time_range
- **Supplement**: If RSS < 3 results and `currents_api_key` is set, call Currents API
- Return `[{title, url, description, source: "news", published_at, extra: {provider: "rss"|"currents"}}]`

**`fetch_currents(query, limit=10, category=None)`**
- Currents API: `https://api.currentsapi.services/v1/search?keywords=...&language=en&apiKey=...`
- 600/day free. Supports language, country, category filters
- Return `[{title, url, description, source: "currents", published_at}]`

**`fetch_stackexchange(query, limit=15, site="stackoverflow")`**
- Stack Exchange API v2.3: `https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q=...&site=...&filter=withbody`
- No API key needed (300/day anonymous)
- Return `[{title, url, body, score, source: "stackexchange", comments: [...]}]`

### A2. Config changes

**File**: `api/core/config.py`
- Add `currents_api_key: str = ""`
- Add `analyze_model: str = "gpt-4.1"` — configurable LLM for analyze agent
- Add `deepseek_api_key: str = ""` — for DeepSeek model option

**File**: `local.env`
- Add `CURRENTS_API_KEY=<key>`
- Add `ANALYZE_MODEL=gpt-4.1` (or `deepseek-chat` to switch)
- Add `DEEPSEEK_API_KEY=<key>` (optional)

**File**: `api/config/news_rss_feeds.json` (new)

```json
{
  "feeds": [
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "NYT World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"},
    {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml"},
    {"name": "AP News (via RSSHub)", "url": "https://rsshub.app/apnews/topics/world-news"},
    {"name": "Reuters (via RSSHub)", "url": "https://rsshub.app/reuters/world"},
    {"name": "Zaobao World (via RSSHub)", "url": "https://rsshub.app/zaobao/realtime/world"}
  ]
}
```

### A3. Configurable LLM model

**File**: `api/services/agent.py`

Replace hardcoded `_get_model_name()` with configurable model:
- If `settings.analyze_model` starts with `deepseek`, use `openai:{model}` with DeepSeek base URL
- PydanticAI supports OpenAI-compatible APIs via model override — DeepSeek's API is OpenAI-compatible
- Set `OPENAI_API_KEY` to `deepseek_api_key` and `OPENAI_BASE_URL` to `https://api.deepseek.com` when using DeepSeek
- Default: `openai:gpt-4.1` (current behavior, no change needed)

```python
def _get_model_name() -> str:
    return settings.analyze_model or "gpt-4.1"

# In analyze_topic(), before running agent:
if "deepseek" in settings.analyze_model:
    os.environ["OPENAI_API_KEY"] = settings.deepseek_api_key
    os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com"
else:
    os.environ.setdefault("OPENAI_API_KEY", settings.effective_openai_key)
```

### A4. New tool functions

**File**: `api/services/tools.py` (append 4 new tool functions)

Follow existing `fetch_reddit_tool` pattern: `RunContext` signature, cache check, `relevance_filter`, adaptive refetch. Per-item truncation: body ≤400 chars, comments top 5 at ≤200 chars each.

**`fetch_hackernews_tool(ctx: RunContext, query: str) -> str`**
- Docstring: "Fetch Hacker News discussions. Best for: tech/startup news, developer opinions, Show HN projects, Y Combinator ecosystem."

**`fetch_news_tool(ctx: RunContext, query: str) -> str`**
- Docstring: "Fetch news articles from major outlets (BBC, NYT, Reuters, etc.) and Currents API. Best for: breaking news, current events, world affairs, politics, business, geopolitics."

**`fetch_stackexchange_tool(ctx: RunContext, query: str) -> str`**
- Docstring: "Fetch Stack Overflow / Stack Exchange Q&A. Best for: programming problems, technical questions, best practices, developer knowledge base."

**`fetch_web_tool(ctx: RunContext, url: str) -> str`**
- Docstring: "Scrape a specific URL using Firecrawl. Use ONLY as last resort when no other tool covers the needed source."
- Takes URL (not query), NO relevance filter, truncate to 5000 chars
- Reuses existing `_smart_fetch(url)` from crawler.py

### A5. Register tools + update system prompt

**File**: `api/services/agent.py`

- Import 4 new tools, add to `tools=[...]` in `create_agent()`
- Update `SYSTEM_PROMPT`:

```
Tools available:
- fetch_reddit_tool: User discussions, opinions, community reactions on any topic
- fetch_youtube_tool: Video reviews, tutorials, commentary, visual content
- fetch_amazon_tool: Product reviews, ratings, consumer sentiment
- fetch_hackernews_tool: Tech/startup community, developer opinions, Show HN projects
- fetch_news_tool: Breaking news, current events, world affairs, politics, business (BBC, NYT, Reuters, etc.)
- fetch_stackexchange_tool: Technical Q&A, programming problems, best practices (Stack Overflow)
- fetch_web_tool: Scrape a specific URL — last resort when no other tool covers the source
- clean_noise_tool: Additional text cleanup if needed

Strategy — pick 2-4 tools most relevant to the query, do NOT call all tools:
- Tech/startup topics → HN + Reddit + YouTube
- Products/brands → Reddit + YouTube + Amazon
- Current events/world affairs → News + HN + Reddit
- Programming questions → Stack Exchange + HN (do NOT use Reddit for programming)
- General research → Reddit + YouTube + News
- Use fetch_web_tool only when you need a specific URL not covered by other tools.
```

### A6. Update schemas and cache config

**File**: `api/models/schemas.py`
- Expand `TopDiscussion.source` Literal: add `"hackernews"`, `"news"`, `"currents"`, `"stackexchange"`, `"web"`

**File**: `api/services/cache.py`
- Add to `_FETCH_LIMITS`: `hackernews`, `news`, `stackexchange`, `web`

### A7. Tests

**File**: `api/tests/test_services/test_agent.py` — update tool name assertions
**File**: `api/tests/test_services/test_tools.py` — add tests for each new tool with mocked crawlers

---

## Part B: Multi-Topic Digests

### Topic definitions

| Topic ID | Display Name | Description | Collectors |
|----------|-------------|-------------|------------|
| `ai` | AI Intelligence | AI/ML ecosystem (existing) | arXiv, GitHub, RSS (AI blogs), Bluesky |
| `geopolitics` | Geopolitics & Conflict | World politics, conflicts, with trade/economy impact | News RSS, Currents (world/politics), HN |
| `climate` | Climate & Environment | Climate change, environment, energy policy | Climate RSS, Currents (environment) |
| `health` | Health & Medical | Medical breakthroughs, disease, public health | Health RSS, Currents (health) |

### B1. Per-topic RSS feed configs

**File**: `api/config/news_rss_feeds.json` (already created in A2 — used by `geopolitics` topic)

**File**: `api/config/climate_rss_feeds.json` (new)
```json
{
  "feeds": [
    {"name": "Guardian Climate", "url": "https://www.theguardian.com/environment/climate-crisis/rss"},
    {"name": "Carbon Brief", "url": "https://www.carbonbrief.org/feed"},
    {"name": "Climate.gov", "url": "https://www.climate.gov/rss.xml"},
    {"name": "BBC Science & Environment", "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"},
    {"name": "InsideClimate News", "url": "https://insideclimatenews.org/feed"}
  ]
}
```

**File**: `api/config/health_rss_feeds.json` (new)
```json
{
  "feeds": [
    {"name": "WHO News", "url": "https://www.who.int/rss-feeds/news-english.xml"},
    {"name": "NIH News", "url": "https://www.nih.gov/news-events/news-releases/feed"},
    {"name": "BBC Health", "url": "https://feeds.bbci.co.uk/news/health/rss.xml"},
    {"name": "STAT News", "url": "https://www.statnews.com/feed/"},
    {"name": "Medical News Today", "url": "https://rss.medicalnewstoday.com/featurednews.xml"}
  ]
}
```

### B2. Database migration

**File**: `api/migrations/003_add_digest_topic.sql` (new)

```sql
-- Add topic column to daily_digests
ALTER TABLE daily_digests ADD COLUMN topic VARCHAR(50) DEFAULT 'ai' NOT NULL;
ALTER TABLE daily_digests DROP CONSTRAINT IF EXISTS daily_digests_digest_date_key;
ALTER TABLE daily_digests ADD CONSTRAINT daily_digests_date_topic_key UNIQUE (digest_date, topic);

-- Add topic column to digest_collector_cache
ALTER TABLE digest_collector_cache ADD COLUMN topic VARCHAR(50) DEFAULT 'ai' NOT NULL;
ALTER TABLE digest_collector_cache DROP CONSTRAINT IF EXISTS digest_collector_cache_digest_date_source_key;
ALTER TABLE digest_collector_cache ADD CONSTRAINT digest_collector_cache_date_source_topic_key UNIQUE (digest_date, source, topic);

-- Update claim_digest_generation RPC to accept topic
CREATE OR REPLACE FUNCTION claim_digest_generation(p_date DATE, p_topic VARCHAR DEFAULT 'ai')
RETURNS JSONB ... (same logic but WHERE digest_date = p_date AND topic = p_topic)
```

Run via Supabase MCP.

### B3. Topic-aware collector registry

**File**: `api/services/collectors/base.py`
- Add `topics: list[str]` to `Collector` Protocol
- Add `get_collectors_for_topic(topic: str) -> dict[str, Collector]` helper

Update existing collectors:
- `arxiv_collector.py` — `topics = ["ai"]`
- `github_collector.py` — `topics = ["ai"]`
- `rss_collector.py` — `topics = ["ai"]`
- `bluesky_collector.py` — `topics = ["ai"]`

### B4. New collectors

**File**: `api/services/collectors/news_rss_collector.py` (new)
- `NewsRssCollector` — parameterized by feed config file
- Create 3 instances registered with different topics:
  - `NewsRssCollector(name="news_rss", config="news_rss_feeds.json", topics=["geopolitics"])`
  - `NewsRssCollector(name="climate_rss", config="climate_rss_feeds.json", topics=["climate"])`
  - `NewsRssCollector(name="health_rss", config="health_rss_feeds.json", topics=["health"])`
- Same feedparser pattern as `rss_collector.py`, fetches last 48h

**File**: `api/services/collectors/currents_collector.py` (new)
- `CurrentsCollector` — parameterized by Currents API category
- Create 3 instances:
  - `CurrentsCollector(name="currents_world", category="world,politics", topics=["geopolitics"])`
  - `CurrentsCollector(name="currents_climate", category="environment,science", topics=["climate"])`
  - `CurrentsCollector(name="currents_health", category="health", topics=["health"])`
- Skip gracefully if `currents_api_key` not set

**File**: `api/services/collectors/hackernews_collector.py` (new)
- `HackerNewsCollector` with `topics = ["geopolitics", "ai"]`
- HN top stories via Firebase API, top 30 in parallel
- For geopolitics: filter out Ask HN, Show HN

**File**: `api/services/collectors/__init__.py`
- Import all new collector modules

### B5. Topic-aware digest pipeline

**File**: `api/services/digest_service.py`

With Fly.io, the pipeline is simplified (single-phase, no HTTP trigger):
- `claim_or_get_digest(user_id, access_token, topic="ai")` → pass `p_topic` to RPC
- `run_digest(digest_id, topic="ai")` → single function: collect → analyze → save
  - Use `get_collectors_for_topic(topic)` to get relevant collectors
  - Run collectors in parallel via `asyncio.gather()`
  - Cache collector results in `digest_collector_cache`
  - Call digest agent with collected items
  - Save completed digest
- No more `run_collectors_phase` + `_trigger_analysis_phase` + `run_analysis_phase` split
- Background execution via `asyncio.create_task(run_digest(...))`

### B6. Topic-specific digest agent prompts

**File**: `api/services/digest_agent.py`

Add `topic` param to `analyze_digest(items, topic="ai")`. Each topic gets its own system prompt:

**AI** (existing): Categories — Breakthrough, Research, Tooling, Open Source, Infrastructure, Product, Policy, Safety, Other

**Geopolitics**: Categories — Conflict & Security, Diplomacy, Trade & Sanctions, Political Change, Regional Tensions, Other
- Importance: 5 = global conflict/crisis, 4 = major diplomatic shift, 3 = notable development, 2 = ongoing situation update, 1 = minor

**Climate**: Categories — Policy & Regulation, Extreme Weather, Energy Transition, Research & Data, Activism & Society, Other
- Importance: 5 = global climate milestone, 4 = major policy/disaster, 3 = notable finding, 2 = incremental, 1 = minor

**Health**: Categories — Breakthrough, Disease & Outbreak, Drug & Treatment, Public Health Policy, Research, Other
- Importance: 5 = pandemic-level / major breakthrough, 4 = significant finding, 3 = notable development, 2 = incremental, 1 = minor

**File**: `api/models/digest_schemas.py`
- `DigestItem.category`: change to `str` (categories vary by topic)
- Add `topic: str = "ai"` to `DailyDigestDB`

### B7. API routes

**File**: `api/routes/ai_daily_report.py`
- `GET /api/ai-daily-report/today?topic=ai` — pass to `claim_or_get_digest`
- `GET /api/ai-daily-report/list?topic=ai` — filter by topic
- Remove `/internal/analyze` and `/internal/collect` (no longer needed after Fly.io migration)
- Validate topic is one of: `ai`, `geopolitics`, `climate`, `health`

### B8. Telegram commands

**File**: `api/services/telegram_service.py`

- `/digest` or `/digest_ai` — AI digest (backward compatible)
- `/digest_geo` — Geopolitics & Conflict digest
- `/digest_climate` — Climate digest
- `/digest_health` — Health & Medical digest
- All call `claim_or_get_digest(user_id, token, topic=...)` with respective topic
- Update help text

### B9. Frontend — Topic dropdown

**File**: `frontend/src/pages/AiDailyReport.tsx`
- Replace heading with a dropdown/select or segmented control:
  - "AI Intelligence" | "Geopolitics & Conflict" | "Climate & Environment" | "Health & Medical"
- `useState<'ai' | 'geopolitics' | 'climate' | 'health'>('ai')`
- Pass `?topic=${topic}` to API
- Re-fetch on topic change
- Dynamic heading based on selected topic
- Realtime subscription scoped to current digest_id

**File**: `frontend/src/lib/api.ts`
- `getTodayDigest(topic?: string)` — add topic param
- `getDigestHistory(page, perPage, topic?)` — add topic param

**File**: `frontend/src/pages/AiDailyReportHistory.tsx`
- Same topic dropdown, filter history by topic

**File**: `frontend/src/components/digest/KanbanBoard.tsx`
- Verify category columns are dynamically derived from data (not hardcoded)
- If hardcoded, make dynamic

### B10. Tests

**File**: `api/tests/test_services/test_digest_service.py`
- Existing tests: pass `topic="ai"` explicitly
- New tests: `topic="geopolitics"`, `topic="climate"`, `topic="health"`

---

## Implementation Order

**Phase 0: Fly.io Migration**
1. **0.1-0.4**: Remove Mangum, Dockerfile, fly.toml, health endpoint
2. **0.5**: Deploy to Fly.io + set secrets
3. **0.6-0.8**: Update frontend API base, Telegram webhook, Vercel config
4. **0.9**: Simplify digest pipeline (remove 2-phase hack)
5. **0.10**: Verify everything works on Fly.io

**Phase 1: New Analyze Tools**
6. **A1-A2**: Crawler functions + config (currents key, model config, RSS feeds)
7. **A3**: Configurable LLM model support
8. **A4-A6**: Tool functions + agent registration + schemas + cache
9. **A7**: Analyze tests

**Phase 2: Multi-Topic Digests**
10. **B1-B2**: RSS feed configs + DB migration
11. **B3-B4**: Collector registry + new collectors
12. **B5-B6**: Digest pipeline + topic-specific prompts
13. **B7**: API route changes
14. **B8**: Telegram commands
15. **B9**: Frontend topic dropdown
16. **B10**: Digest tests

---

## Verification

### Phase 0: Fly.io
1. `curl https://smia-agent.fly.dev/api/health` → 200
2. Frontend calls Fly.io backend (CORS, auth all work)
3. Existing analyze + digest work end-to-end on Fly.io
4. Telegram bot responds on new webhook URL
5. `cd api && uv run python -m pytest -v` — all existing tests pass

### Phase 1: Analyze
1. `cd api && uv run python -m pytest tests/test_services/test_agent.py tests/test_services/test_tools.py -v`
2. Test: "Ukraine war" → News + Reddit + HN (no Stack Exchange)
3. Test: "Python async" → Stack Exchange + HN (no Reddit per prompt guidance)
4. Test: "iPhone 16 review" → Reddit + YouTube + Amazon
5. Langfuse traces: confirm tool selection matches guidance
6. Switch `ANALYZE_MODEL=deepseek-chat` + test same queries

### Phase 2: Digest
1. Run migration (existing digests get `topic='ai'`)
2. `GET /api/ai-daily-report/today?topic=ai` — existing behavior
3. `GET /api/ai-daily-report/today?topic=geopolitics` — single-phase pipeline
4. `GET /api/ai-daily-report/today?topic=climate` — climate pipeline
5. `GET /api/ai-daily-report/today?topic=health` — health pipeline
6. Telegram: `/digest_ai`, `/digest_geo`, `/digest_climate`, `/digest_health`
7. Frontend: dropdown switches between all 4 topics
8. `cd api && uv run python -m pytest tests/test_services/test_digest_service.py -v`

---

## Key Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `api/main.py` | Modify | Remove Mangum, add uvicorn runner |
| `Dockerfile` | New | Python 3.12 + uv + deps |
| `fly.toml` | New | Fly.io config (sin region, scale-to-zero) |
| `api/routes/health.py` | New | Health check endpoint |
| `frontend/.env.production` | Modify | Point API to Fly.io |
| `vercel.json` | Modify | Remove backend routes |
| `api/services/crawler.py` | Append | 4 new crawler functions (HN, news, currents, SE) |
| `api/config/news_rss_feeds.json` | New | Geopolitics RSS + RSSHub feeds |
| `api/config/climate_rss_feeds.json` | New | Climate/environment RSS feeds |
| `api/config/health_rss_feeds.json` | New | Health/medical RSS feeds |
| `api/core/config.py` | Modify | Add currents_api_key, analyze_model, deepseek_api_key |
| `api/services/tools.py` | Append | 4 new PydanticAI tool functions |
| `api/services/agent.py` | Modify | Register tools, update prompt, configurable model |
| `api/models/schemas.py` | Modify | Expand source Literal |
| `api/services/cache.py` | Modify | Add fetch limits for new sources |
| `api/migrations/003_add_digest_topic.sql` | New | Topic column + constraint changes |
| `api/services/collectors/base.py` | Modify | Add topics attribute + helper |
| `api/services/collectors/news_rss_collector.py` | New | Parameterized news RSS collector (3 instances) |
| `api/services/collectors/currents_collector.py` | New | Parameterized Currents collector (3 instances) |
| `api/services/collectors/hackernews_collector.py` | New | HN collector |
| `api/services/collectors/__init__.py` | Modify | Import new collectors |
| `api/services/digest_service.py` | Modify | Topic parameter throughout pipeline |
| `api/services/digest_agent.py` | Modify | 4 topic-specific prompts + categories |
| `api/models/digest_schemas.py` | Modify | Flexible categories, topic field |
| `api/routes/ai_daily_report.py` | Modify | Topic query param + validation |
| `api/services/telegram_service.py` | Modify | 4 digest commands |
| `frontend/src/pages/AiDailyReport.tsx` | Modify | Topic dropdown UI |
| `frontend/src/lib/api.ts` | Modify | Topic param in API calls |
| `frontend/src/pages/AiDailyReportHistory.tsx` | Modify | Topic filter |
| `frontend/src/components/digest/KanbanBoard.tsx` | Verify | Dynamic category columns |

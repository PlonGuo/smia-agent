# Plan: Fly.io Backend Migration

## Context

SmIA backend currently runs on Vercel serverless (FastAPI + Mangum). The 60s timeout is becoming a blocker for upcoming features (8 analyze tools, multi-topic digests). Migrating to Fly.io removes this constraint, simplifies the digest pipeline (no 2-phase hack), and stays within the free tier.

**Estimated cost**: $0/month (1 shared-cpu-1x VM, 256MB, scale-to-zero)
**Migration scope**: Backend only. Frontend stays on Vercel.

---

## Steps

### 1. Remove Vercel serverless adapter

**File**: `api/main.py`
- Remove `from mangum import Mangum` and `handler = Mangum(app)`
- Add uvicorn runner: `if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=8080)`
- Keep all FastAPI routes, middleware, CORS unchanged

### 2. Dockerfile

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

EXPOSE 8080
CMD ["uv", "run", "--directory", "api", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

Note: `local.env` is NOT copied — secrets are set via `fly secrets set`.

### 3. Fly.io config

**File**: `fly.toml` (new, project root)

```toml
app = "smia-agent"
primary_region = "sin"

[build]

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
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

### 4. Health check endpoint

**File**: `api/routes/health.py` (new) or add to `api/main.py`
- `GET /api/health` → `{"status": "ok"}`

### 5. CORS update

**File**: `api/main.py`
- Add Fly.io domain to CORS allowed origins
- Ensure Vercel frontend domain is still allowed

### 6. Deploy to Fly.io (manual steps)

```bash
# Install flyctl (if not installed)
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Create app (don't deploy yet)
fly launch --name smia-agent --region sin --no-deploy

# Set all secrets from local.env
fly secrets set \
  SUPABASE_URL="..." \
  SUPABASE_ANON_KEY="..." \
  SUPABASE_SERVICE_KEY="..." \
  OPENAI_API_KEY="..." \
  OPEN_AI_API_KEY="..." \
  FIRECRAWL_API_KEY="..." \
  YOUTUBE_API_KEY="..." \
  LANGFUSE_PUBLIC_KEY="..." \
  LANGFUSE_SECRET_KEY="..." \
  LANGFUSE_BASE_URL="..." \
  TELEGRAM_BOT_TOKEN="..." \
  TELEGRAM_WEBHOOK_SECRET="..." \
  INTERNAL_SECRET="..." \
  RESEND_API_KEY="..." \
  GMAIL_ADDRESS="..." \
  GMAIL_APP_PASSWORD="..." \
  SCRAPER_API_KEY="..." \
  APP_URL="https://smia-agent.fly.dev"

# Deploy
fly deploy

# Verify
fly status
curl https://smia-agent.fly.dev/api/health
```

### 7. Update frontend

**File**: `frontend/.env.production`
- Change `VITE_API_BASE` to `https://smia-agent.fly.dev/api`

### 8. Update Telegram webhook

```bash
TELEGRAM_BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' local.env | cut -d= -f2)
TELEGRAM_WEBHOOK_SECRET=$(grep '^TELEGRAM_WEBHOOK_SECRET=' local.env | cut -d= -f2)
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://smia-agent.fly.dev/api/telegram/webhook&secret_token=${TELEGRAM_WEBHOOK_SECRET}"
```

### 9. Remove Vercel backend config

**File**: `vercel.json`
- Remove `/api/` route rewrites
- Keep frontend-only config (SPA routing, redirects)

### 10. Simplify digest pipeline

**File**: `api/services/digest_service.py`
- Merge 2-phase pipeline into single `run_digest(digest_id)`:
  - Run all collectors via `asyncio.gather()`
  - Cache results in `digest_collector_cache`
  - Run LLM analysis
  - Save completed digest
  - Send notifications
- Remove `_trigger_analysis_phase()` (HTTP self-call hack)
- Replace Vercel `BackgroundTask` with `asyncio.create_task()`

**File**: `api/routes/ai_daily_report.py`
- Remove `/internal/analyze` and `/internal/collect` endpoints
- Update `GET /today` to use `asyncio.create_task()` for background generation

### 11. Remove Mangum dependency

**File**: `api/pyproject.toml`
- Remove `mangum` from dependencies

### 12. Config: env loading on Fly.io

**File**: `api/core/config.py`
- Fly.io sets env vars directly (via `fly secrets`), so `local.env` file loading is dev-only
- Current code already handles this: `model_config = {"env_file": str(_env_file), "extra": "ignore"}` — if file missing, falls back to env vars

---

## Verification

1. `curl https://smia-agent.fly.dev/api/health` → `{"status": "ok"}`
2. Frontend (Vercel) → Fly.io backend: login, analyze, digest all work
3. Telegram bot responds on new webhook
4. AI digest generates in single phase (check Fly.io logs: `fly logs`)
5. `cd api && uv run python -m pytest -v` — all tests pass locally
6. Check Langfuse traces still flowing

## Rollback

If anything goes wrong:
- Frontend: revert `VITE_API_BASE` to Vercel URL, redeploy
- Telegram: re-register webhook to Vercel URL
- Vercel backend still exists, just redeploy with Mangum

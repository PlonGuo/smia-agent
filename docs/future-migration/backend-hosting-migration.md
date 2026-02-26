# Backend Hosting Migration Plan

## Why Migrate Off Vercel Serverless?

SmIA's backend (FastAPI + LLM agent pipeline) is deployed on Vercel as serverless functions via Mangum. This works but introduces significant architectural friction:

### Current Pain Points

1. **60-second function timeout** — LLM calls and multi-step pipelines frequently approach or exceed this limit. We had to split the digest pipeline into two phases (collectors + analysis), each getting its own HTTP invocation for a fresh 60s budget.

2. **BackgroundTask is unreliable** — Vercel can kill the function instance after the HTTP response is sent, meaning `BackgroundTask` may never execute or get interrupted mid-execution. This caused Telegram `/digest` to silently fail (no response to user).

3. **Workarounds add complexity** — To cope with the above, we introduced:
   - Two-phase pipeline with self-invoking HTTP calls (`/internal/analyze`)
   - Staleness recovery (5-minute timeout detection + automatic reset)
   - Telegram handlers switched from BackgroundTask to synchronous `await`
   - Frontend polling + database status tracking instead of relying on response

4. **Cold starts** — Each function invocation may incur a cold start, adding latency to every request.

5. **No WebSocket support** — Future features like streaming LLM output or real-time updates are impossible on serverless.

### What Works Fine on Vercel

- **Frontend** — Static React app with Vite, perfect fit for Vercel's edge CDN. No reason to move this.
- **Simple CRUD endpoints** — Short-lived, stateless requests work well as serverless functions.

---

## Target Architecture

```
Vercel (Frontend)  ──HTTPS──>  Long-running Backend (FastAPI + uvicorn)
                                    │
                                    ├── BackgroundTask (works normally)
                                    ├── LLM calls (no timeout pressure)
                                    ├── WebSocket (future: streaming)
                                    └── Telegram webhook handler
```

The frontend stays on Vercel. The backend moves to a platform that supports long-running processes.

---

## Platform Comparison (as of early 2026)

| Platform | Free Tier? | Specs | Always-On? | Credit Card? | Deploy Experience |
|----------|-----------|-------|------------|-------------|-------------------|
| **Oracle Cloud (Always Free)** | Yes (permanent) | 4 ARM cores, 24GB RAM | Yes | Yes (verification) | Manual (SSH + systemd) |
| **Render** | Yes | 512MB, 0.1 CPU | No (sleeps after 15min) | Unclear | `git push` auto-deploy |
| **Koyeb** | Yes | 512MB, 0.1 vCPU | No (scale-to-zero) | Yes | `git push` auto-deploy |
| **Railway** | Trial only, then $1/mo | 1GB, shared vCPU | Yes (burns credit) | No (trial) | `git push` auto-deploy |
| **Fly.io** | No (removed 2024) | — | — | Yes | CLI deploy |
| **VPS (Hetzner/DO)** | No | From 1 vCPU, 1GB | Yes | Yes | Manual (Docker/systemd) |
| **Railway Hobby** | $5/mo | 8GB, 8 vCPU | Yes | Yes | `git push` auto-deploy |
| **Render Starter** | $7/mo | 512MB, 0.5 CPU | Yes (no sleep) | Yes | `git push` auto-deploy |

### Recommended Options

**Best free option: Oracle Cloud Always Free**
- 4 ARM cores + 24GB RAM, permanently free, truly always-on
- Tradeoff: full IaaS — you manage the VM, install dependencies, configure systemd, handle deployments
- ARM architecture requires compatible Python packages (most work fine)

**Best paid option: Railway Hobby ($5/mo)**
- `git push` auto-deploy, great DX, no sleep behavior
- $5/mo includes $5 usage credit, enough for a single FastAPI service
- Closest experience to Vercel but for long-running backends

**Best free PaaS: Render Free Tier**
- 512MB RAM, auto-deploy from Git
- Major caveat: sleeps after 15 minutes of inactivity, ~50s cold start
- Acceptable if traffic is regular enough to keep it warm

---

## Migration Steps (High Level)

### Phase 1: Prepare Backend for Traditional Deployment

1. **Remove Mangum wrapper** — Currently `api/index.py` wraps FastAPI with Mangum for Vercel. For a traditional deployment, run uvicorn directly.

2. **Simplify digest pipeline** — With no 60s timeout, the two-phase HTTP chain can be collapsed:
   - Remove `/internal/analyze` and `/internal/collect` endpoints
   - Run collectors + LLM analysis in a single BackgroundTask
   - Remove staleness recovery logic (or keep as safety net)

3. **Simplify Telegram handler** — Can use BackgroundTask again since the process won't be killed.

4. **Add Dockerfile**:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY . .
   RUN pip install uv && uv sync
   CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

5. **Environment variables** — Move from Vercel env config to the new platform's env management.

### Phase 2: Deploy and Test

1. Deploy backend to chosen platform
2. Update frontend API base URL (environment variable in Vercel)
3. Update Telegram webhook URL to point to new backend
4. Verify all flows: HTTPS digest, Telegram `/digest`, analysis pipeline
5. Monitor for a few days alongside Vercel (dual-run if possible)

### Phase 3: Cutover

1. Point frontend to new backend permanently
2. Update Telegram webhook
3. Remove Vercel serverless function config (keep frontend config)
4. Clean up migration-specific code (Mangum wrapper, phase-splitting, etc.)

---

## What We Gain

- **No timeout limits** — LLM calls can take as long as needed
- **Reliable BackgroundTask** — Process stays alive, tasks complete
- **Simpler architecture** — No phase-splitting, no self-invoking HTTP chains, no staleness recovery hacks
- **WebSocket support** — Enables future streaming features
- **Connection pooling** — Database and HTTP connections can be reused across requests
- **Lower latency** — No cold starts (always-on)

## What We Lose

- **Zero-ops deployment** — Need to manage infrastructure (unless using Railway/Render paid)
- **Auto-scaling** — Serverless scales to zero cost when idle; a VPS runs 24/7
- **Vercel's edge network** — Backend requests won't benefit from edge CDN (but API calls don't need it)

---

## Decision

No immediate migration planned. Current Vercel serverless setup works with the workarounds in place. This document serves as the reference for when we decide to migrate, likely triggered by:

- Adding features that need WebSocket or long-running tasks
- The workaround complexity becoming a maintenance burden
- Cost optimization (if Vercel function usage grows)

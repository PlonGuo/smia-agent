# MCP Server — Implementation Record

**Date**: 2026-03-12
**Branch**: development
**Status**: Done

## Context

Expose SmIA's AI Digest content via a public MCP server so AI clients (Claude Desktop, Cursor, Windsurf) can fetch digests directly without requiring a token or account.

## Changes Made

### Backend

**`api/pyproject.toml`**
- Added `mcp>=1.26.0` to dependencies

**`api/services/digest_service.py`**
- Made `user_id` and `access_token` params optional (`= None`) in `claim_or_get_digest()`
- No other changes needed — the function already used service role client internally

**`api/routes/mcp_server.py`** (new file)
- `FastMCP` server with 3 tools:
  - `get_digest(topic)` — on-demand digest with non-blocking trigger
  - `get_digest_history(topic, days)` — last N days of summaries (max 30)
  - `list_topics()` — available topics from `DIGEST_TOPICS` config
- `_format_digest()` helper outputs AI-readable markdown
- Logging follows `[MCP]` prefix convention

**`api/index.py`**
- Mounted MCP ASGI sub-app at `/mcp` via `app.mount("/mcp", mcp.streamable_http_app())`

### Frontend

**`frontend/src/components/landing/TutorialSection.tsx`**
- Added 4th tutorial slide "Connect via MCP" with `Bot` icon
- Added `McpMockup` component: copyable JSON config block + available tools list
- Added `isMcp?: boolean` field to `TutorialSlide` interface to switch between image and code mockup

## Key Design Decisions

- **Fully public**: no auth required — digest content is already public
- **On-demand generation**: triggers only when today's digest doesn't exist, saving LLM costs
- **Non-blocking**: returns immediately with "try again in 1 minute" message; uses existing DB lock to prevent duplicate triggers
- **No new Fly.io machine**: MCP runs as a mounted ASGI sub-app on port 8080 alongside the existing FastAPI app

## End-User Config

```json
{
  "mcpServers": {
    "smia": {
      "url": "https://smia-agent.fly.dev/mcp"
    }
  }
}
```

Supported clients: Claude Desktop, Cursor, Windsurf (any MCP-compatible HTTP client).

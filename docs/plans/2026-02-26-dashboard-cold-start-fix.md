# Plan: Fix Dashboard Cold Start Slow Loading

**Date**: 2026-02-26
**Status**: Done
**Branch**: development
**Commit**: 59aebc2

## Context

The Dashboard page took 5-10+ seconds to load after the Vercel serverless function went cold (idle for a few minutes). When warm, it loaded in ~1s. Root cause: Python cold start on Vercel Hobby plan (~2-3.5s for runtime + 8 router imports + Langfuse init), plus auth verification + two sequential DB queries (~1s).

Vercel Hobby plan limits cron jobs to once/day, so a keep-alive cron was not viable. The solution focused on making cold starts invisible via frontend caching.

## Changes Made

### 1. Frontend: Stale-While-Revalidate Cache (biggest UX impact)

**File:** `frontend/src/pages/Dashboard.tsx`

- Added `sessionStorage`-based SWR cache for dashboard report data
- On mount: if cached data exists for current params (page/sentiment/search), shown **instantly** without skeleton
- Fresh data always fetched in background and updates UI silently
- Cache key is param-aware: `smia_dashboard:page=1&sentiment=&search=`
- Cache invalidated on report delete to prevent stale data
- Error toasts suppressed when cached data is available as fallback
- Follows existing `Analyze.tsx` sessionStorage pattern

### 2. Backend: Count Query Optimization

**File:** `api/services/database.py` (line 149)

- Changed `select("*", count=CountMethod.exact)` to `select("id", count=CountMethod.exact)`
- Count query doesn't use returned rows — lighter select for PostgREST

## Result

| Scenario | Before | After |
|---|---|---|
| Return to Dashboard after cold start | 5-10s skeleton | **Instant** (cached), silent background refresh |
| First visit in session | 5-10s skeleton | 5-10s skeleton (unavoidable on Hobby plan) |
| Previously visited filter/page | ~1s skeleton | **Instant** |

## Verification

- 256 backend tests pass
- Frontend builds successfully
- No new dependencies added

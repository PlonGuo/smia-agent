# Plan: Open Digest Access + Analyze Daily Limit

## Context

Currently the AI Digest feature has a multi-tier permission system (admin/approved/pending/rejected/none) requiring admin approval before users can view digests. The user wants to **remove this gate** so any authenticated user can access digests.

For the Analyze feature, the current rate limit is 100/hour which is too generous. The user wants a **5 requests per day** limit per user. This requires changing the rate-limiting logic from hourly to daily, and reducing the cap.

## Changes

### 1. Backend — Remove digest permission checks

**Files to modify:**
- [api/routes/ai_daily_report.py](api/routes/ai_daily_report.py) — Remove `get_digest_access_status()` checks from:
  - `GET /today` (line 42-47) — remove the access check + 403
  - `GET /list` (line 73-75) — remove the access check + 403
  - `GET /{digest_id}` (line 140-142) — remove the access check + 403
  - `POST /share` (line 209-211) — remove the access check + 403
  - `GET /status` (line 57-63) — simplify to always return "approved" (or remove entirely)
  - `POST /access-request` (line 163-195) — keep but it becomes a no-op (or remove)
- Remove unused imports of `get_digest_access_status` from the route file

### 2. Frontend — Remove digest permission gating

**Files to modify:**
- [frontend/src/pages/AiDailyReport.tsx](frontend/src/pages/AiDailyReport.tsx) — Remove permission-based conditional rendering:
  - Remove `useDigestPermissions` hook usage
  - Remove the "none"/"rejected" → AccessRequestModal branch
  - Remove the "pending" → pending message branch
  - Always fetch and show the digest for authenticated users
- [frontend/src/hooks/useDigestPermissions.ts](frontend/src/hooks/useDigestPermissions.ts) — Can be left in place (may be used by admin page) or simplified

### 3. Backend — Change Analyze rate limit to 5/day (shared across web + telegram)

Since web and Telegram are the same user account (linked via `user_bindings`), the limit is **per user_id regardless of source** — not separate buckets.

**Files to modify:**
- [api/core/rate_limit.py](api/core/rate_limit.py):
  - Replace separate `WEB_RATE_LIMIT` / `TELEGRAM_RATE_LIMIT` with a single `DAILY_LIMIT = 5`
  - Remove the `source` parameter — count ALL reports for the user in the last 24h (or since start of day UTC)
  - Change time window from `timedelta(hours=1)` to start-of-day UTC (`datetime.now(UTC).replace(hour=0, minute=0, second=0)`)
  - Update function signature and docstring
- [api/routes/analyze.py](api/routes/analyze.py):
  - Update `check_rate_limit()` call to remove `source="web"` arg
  - Update 429 error message to "5 analyses per day"
- [api/services/telegram_service.py](api/services/telegram_service.py):
  - Update `check_rate_limit()` call to remove `source="telegram"` arg
  - Update the rate limit error message to "5 analyses per day"

### 4. Frontend — Show daily limit info (optional nice-to-have)

- Consider showing remaining daily quota on the Analyze page (the `check_rate_limit` already returns `remaining`)

## What NOT to change

- Admin panel and admin routes — keep them functional for other admin tasks
- Digest share tokens — keep working as-is
- Digest access request tables — no schema migration needed, just stop checking them
- The `admins`, `digest_authorized_users`, `digest_access_requests` tables stay in DB (no destructive migration)

## Verification

1. **Digest access**: Log in as a non-admin, non-approved user → should see the digest directly without any access request flow
2. **Analyze limit**: Make 5 analyze requests → 6th should return 429 with "5 analyses per day" message
3. **Telegram limit**: Test via Telegram bot if accessible
4. **Existing features**: Admin panel still works, share links still work, digest history still works

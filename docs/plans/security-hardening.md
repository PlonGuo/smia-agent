# Security Hardening

> **Status**: Done (2026-03-06)
> **Branch**: `security/hardening`
> **Priority**: High

## Current Security Baseline

Already implemented:
- [x] Rate limiting (per-user) via Supabase-based check
- [x] JWT authentication (Supabase `get_user(token)`)
- [x] Row-Level Security (RLS) on all user tables
- [x] Pydantic input validation with field constraints
- [x] Environment variable secret management (`local.env`, `.strip()` on tokens)
- [x] Environment detection (dev/preview/production)

## Completed (2026-03-06)

### High Priority

- [x] **Remove `/api/debug` endpoint**: Deleted unauthenticated endpoint that leaked API key prefixes, lengths, and system info
- [x] **Fix `INTERNAL_SECRET`**: Removed hardcoded default, added empty-check guard, set strong secret in Vercel env vars
- [x] **CORS restriction**: Restricted `allow_origins` to `smia-agent.vercel.app` + preview domains + localhost (dev only)
- [x] **Telegram webhook HMAC verification**: Added `X-Telegram-Bot-Api-Secret-Token` header validation, re-registered webhook with `secret_token`
- [x] **Security headers**: Added via `vercel.json` — HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy
- [x] **Global exception handler**: Sanitized error responses in production (no stack traces, exception types)
- [x] **API response filtering**: Changed analyze error detail from `f"{type(exc).__name__}: {exc}"` to generic message

### Deferred (not blocking)

- [ ] **IP-based rate limiting**: Skipped — core attack paths already blocked by INTERNAL_SECRET + Telegram HMAC
- [ ] **DDoS protection**: Evaluate Vercel Firewall / Cloudflare if traffic increases
- [ ] **Content Security Policy (CSP)**: Requires careful tuning to avoid breaking frontend
- [ ] **Dependency vulnerability scanning**: Set up `pip-audit` / Dependabot
- [ ] **Structured security logging**: Audit trail for admin operations

## Files Modified

| File | Change |
|------|--------|
| `api/index.py` | Removed `/api/debug`, restricted CORS, added global exception handler |
| `api/core/config.py` | Removed hardcoded `internal_secret` default, added `telegram_webhook_secret` |
| `api/routes/telegram.py` | Added `X-Telegram-Bot-Api-Secret-Token` verification |
| `api/routes/ai_daily_report.py` | Added empty-secret guard on internal endpoints |
| `api/routes/analyze.py` | Sanitized error detail message |
| `vercel.json` | Added security headers (HSTS, X-Frame-Options, etc.) |

## Vercel Env Vars Added

| Variable | Environments |
|----------|-------------|
| `INTERNAL_SECRET` | Production, Preview |
| `TELEGRAM_WEBHOOK_SECRET` | Production, Preview |

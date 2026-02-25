# Security Hardening — TODO

> **Status**: Not started. Tackle after AI Daily Report feature is complete.
> **Priority**: High — should be done before public launch.

## Current Security Baseline

Already implemented:
- [x] Rate limiting (100/hr web, 10/hr telegram) via Supabase-based check
- [x] JWT authentication (Supabase `get_user(token)`)
- [x] Row-Level Security (RLS) on `analysis_reports`, `user_bindings`
- [x] Pydantic input validation with field constraints
- [x] Environment variable secret management (`local.env`, `.strip()` on tokens)
- [x] Environment detection (dev/preview/production)

## TODO

### High Priority

- [ ] **CORS restriction**: Change `allow_origins=["*"]` to actual production domain(s) in `api/index.py`
- [ ] **Security headers middleware**: Add `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, `Content-Security-Policy`, `X-XSS-Protection`
- [ ] **Rate limiting for new endpoints**: Apply rate limits to `/api/ai-daily-report/*`, `/api/admin/*`, `/api/bookmarks/*`, `/api/feedback/*`
- [ ] **RLS for new tables**: Verify RLS policies on all digest-related tables match the plan
- [ ] **Telegram webhook HMAC-SHA256 verification**: Validate webhook requests with Telegram's secret token signature (currently only token-in-URL)

### Medium Priority

- [ ] **DDoS protection strategy**: Evaluate Vercel Firewall rules / Cloudflare proxy for production
- [ ] **Audit unauthenticated endpoints**: Review `/api/bind/confirm`, `/telegram/webhook`, shared digest view — ensure they can't be abused
- [ ] **Input sanitization**: Review all user-provided text fields (access request reason, etc.) for XSS vectors before rendering in frontend
- [ ] **API response filtering**: Ensure no internal data leaks in error responses (stack traces, DB details)

### Low Priority

- [ ] **Dependency vulnerability scanning**: Set up `pip-audit` or GitHub Dependabot for backend, `pnpm audit` for frontend
- [ ] **Content Security Policy (CSP)**: Fine-tune CSP headers for production
- [ ] **Logging & monitoring**: Structured logging for security events (failed auth, rate limit hits, suspicious patterns)

## Files to Modify

| File | Change |
|------|--------|
| `api/index.py` | CORS origins, security headers middleware |
| `api/core/rate_limit.py` | Extend to new endpoints |
| `api/routes/telegram.py` | HMAC signature verification |
| `vercel.json` | Security headers at Vercel level |
| `frontend/vite.config.ts` | CSP meta tags for dev |

# Plan: Resend Email on Push to Main (Final)

## Context
When code is pushed to `main`, email all registered users about the update using Resend. Email content = git commit messages. Keep it simple — no idempotency table, no preferences table. Add opt-out later if needed.

**Existing infrastructure to reuse:**
- Resend configured: `resend` package (v2.23.0), `RESEND_API_KEY` in config
- `_send_email(to, subject, html)` helper in `api/services/email_service.py`
- Internal endpoint auth: `x-internal-secret` header (see `api/routes/ai_daily_report.py:246`)

## Implementation Steps

### 1. `api/services/database.py` — Add `get_all_user_emails()`
- Use `get_supabase_client()` (service-role) -> `client.auth.admin.list_users()`
- Handle pagination (1000 users/page)
- Return all `.email` values
- Follow `get_all_admin_emails()` pattern (line 368)

### 2. `api/services/email_service.py` — Add `send_update_notification()`
- Takes `commits: list[dict]`, `recipient_emails: list[str]`
- **Filter out noise**: skip commits where message starts with `chore:`, `docs:`, `ci:`, or is a merge commit (`Merge pull request`, `Merge branch`)
- If no meaningful commits remain after filtering, skip sending entirely
- Builds styled HTML with commit SHA (short), message, author, link
- **Dark mode compatible**: use semantic colors that work in both light/dark email clients (avoid hardcoded white backgrounds)
- Uses **Resend Batch API** (`resend.Batch.send()`) — up to 100 emails per call
- Returns count of successfully sent emails

### 3. Create `api/routes/internal.py`
- `APIRouter(prefix="/api/internal", tags=["internal"])`
- `POST /api/internal/notify-update`
- Auth: `x-internal-secret` header
- Body: `{"commits": [{"id", "message", "author", "url"}, ...]}`
- **Log timing**: record start time, log total elapsed at end for Vercel timeout awareness
- Calls `get_all_user_emails()` then `send_update_notification()`
- Returns `{"status": "ok", "emails_sent": N, "total_users": N, "elapsed_ms": N}`

### 4. `api/index.py` — Register `internal_router`

### 5. Create `.github/workflows/notify-update.yml`
- Trigger: `push` to `main` branch (no `paths-ignore` — notify on every push)
- Extracts `github.event.commits` via `toJSON()`
- Uses `jq` to build payload: `{commits: [...]}`
- `curl` POST to `${SMIA_API_URL}/api/internal/notify-update` with `x-internal-secret` header
- **Required GitHub Secrets:** `SMIA_API_URL`, `INTERNAL_SECRET`

### 6. Create `api/tests/test_routes/test_internal.py`
- Test: rejects bad secret (403)
- Test: skips when no commits
- Test: sends emails to all users (mocks)
- Test: skips when no users found

## Files Modified/Created
| File | Action |
|------|--------|
| `api/services/database.py` | Add `get_all_user_emails()` |
| `api/services/email_service.py` | Add `send_update_notification()` using Batch API |
| `api/routes/internal.py` | **Create** — notify-update endpoint |
| `api/index.py` | Register `internal_router` |
| `.github/workflows/notify-update.yml` | **Create** — GH Actions workflow |
| `api/tests/test_routes/test_internal.py` | **Create** — tests |

## Manual Steps (you)
1. **GitHub repo secrets** (already done): `SMIA_API_URL`, `INTERNAL_SECRET`
2. **Vercel env var** (already done): `RESEND_API_KEY`
3. **Optional**: Verify custom domain in Resend to avoid spam folder

### 7. Test email rendering before merge
- Send a real test email to yourself via the local endpoint
- Verify rendering in: Gmail (web), Apple Mail (dark mode), mobile client
- Check that commit links work and HTML doesn't break

## Verification
1. `cd api && uv run python -m pytest -v` — all tests pass
2. Local curl test:
   ```
   curl -X POST http://localhost:8000/api/internal/notify-update \
     -H "Content-Type: application/json" \
     -H "x-internal-secret: <secret>" \
     -d '{"commits": [{"id":"abc1234","message":"feat: new feature","author":"dev","url":"#"},{"id":"bcd2345","message":"chore: bump deps","author":"dev","url":"#"}]}'
   ```
   Verify: only "feat: new feature" appears in the email (chore filtered out)
3. Check elapsed_ms in response — should be well under 60s
4. Push to main and verify email arrives in real inbox (not spam)

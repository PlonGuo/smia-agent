# Fly.io Backend Setup Instructions

These are the manual steps required after the code migration is complete.

## Prerequisites

- A Fly.io account (free tier)
- `local.env` file with all secrets
- Access to GitHub repo settings (for secrets)

## 1. Install Fly.io CLI

```bash
curl -L https://fly.io/install.sh | sh
```

## 2. Login & Create App

```bash
fly auth login
fly launch --name smia-agent --region sin --no-deploy
```

> Region `sin` = Singapore. Choose the closest region to your users/database.

## 3. Set All Secrets

Copy values from your `local.env` file:

```bash
fly secrets set \
  SUPABASE_URL="<value>" \
  SUPABASE_ANON_KEY="<value>" \
  SUPABASE_SERVICE_KEY="<value>" \
  OPENAI_API_KEY="<value>" \
  OPEN_AI_API_KEY="<value>" \
  FIRECRAWL_API_KEY="<value>" \
  YOUTUBE_API_KEY="<value>" \
  LANGFUSE_PUBLIC_KEY="<value>" \
  LANGFUSE_SECRET_KEY="<value>" \
  LANGFUSE_BASE_URL="https://us.cloud.langfuse.com" \
  TELEGRAM_BOT_TOKEN="<value>" \
  TELEGRAM_WEBHOOK_SECRET="<value>" \
  INTERNAL_SECRET="<value>" \
  RESEND_API_KEY="<value>" \
  GMAIL_ADDRESS="<value>" \
  GMAIL_APP_PASSWORD="<value>" \
  SCRAPER_API_KEY="<value>" \
  APP_URL="https://smia-agent.fly.dev"
```

## 4. Deploy

```bash
fly deploy
fly status
curl https://smia-agent.fly.dev/api/health
```

Expected response: `{"status": "ok"}`

> **Important**: Test the Fly.io deployment directly before updating frontend or Telegram webhook. Verify health check, try a login via direct API call, etc.

## 5. Register Telegram Webhook

Point the Telegram bot to the new Fly.io URL:

```bash
TELEGRAM_BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' local.env | cut -d= -f2)
TELEGRAM_WEBHOOK_SECRET=$(grep '^TELEGRAM_WEBHOOK_SECRET=' local.env | cut -d= -f2)
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://smia-agent.fly.dev/api/telegram/webhook&secret_token=${TELEGRAM_WEBHOOK_SECRET}"
```

## 6. Update GitHub Secret

Go to GitHub repo -> Settings -> Secrets and variables -> Actions:
- Update `SMIA_API_URL` to `https://smia-agent.fly.dev`

## 7. Trigger Frontend Redeploy

Push to main or manually trigger a Vercel redeploy so it picks up the new `frontend/.env.production` with the Fly.io API URL.

## Verification Checklist

After completing all steps, verify:

1. `curl https://smia-agent.fly.dev/api/health` returns `{"status": "ok"}`
2. Frontend (Vercel) login and analyze a topic work end-to-end
3. AI digest generates (check `fly logs` for single-phase execution)
4. Telegram commands work: `/start`, `/analyze test`, `/digest`
5. Langfuse traces are flowing
6. Push to main triggers notify-update email

## Monitoring

- View logs: `fly logs`
- Check status: `fly status`
- Monitor memory: if OOM kills occur, bump to 512MB: `fly scale memory 512`
- Rollback: `fly releases` then `fly deploy --image <previous-image>`

## Rollback Plan

If anything goes wrong:

1. Frontend: change `VITE_API_BASE` back to `/api` in `.env.production`, redeploy Vercel
2. Restore `vercel.json` backend rewrites for `/api/`
3. Re-register Telegram webhook to Vercel URL
4. Vercel backend still deploys from the same codebase

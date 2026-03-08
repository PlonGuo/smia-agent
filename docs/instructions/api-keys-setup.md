# API Keys Setup — Expand Data Sources Feature

This guide covers all new API keys needed for the `expand-data-sources` branch.

After obtaining each key, add it to `local.env` in the project root.

---

## 1. Guardian Content API

**Free tier**: 5,000 calls/day, 12 calls/sec

**Steps**:
1. Go to https://open-platform.theguardian.com/access/
2. Fill in name, email, and a short project description
3. Click "Register"
4. API key will be sent to your email immediately

**Add to `local.env`**:
```
GUARDIAN_API_KEY=your-key-here
```

---

## 2. Tavily Search API

**Free tier**: 1,000 credits/month (~33/day), no credit card required

**Steps**:
1. Go to https://app.tavily.com/home
2. Sign up / sign in (Google or email)
3. Copy your API key from the dashboard (or click "+" to create a new one)
4. Choose "Development Key" (100 req/min, sufficient for our use)

**Add to `local.env`**:
```
TAVILY_API_KEY=tvly-your-key-here
```

---

## 3. Currents News API

**Free tier**: 600 calls/day

**Steps**:
1. Go to https://currentsapi.services/en
2. Click "Get Free API Key" / Sign up
3. Log in and copy your API key from the dashboard

**Add to `local.env`**:
```
CURRENTS_API_KEY=your-key-here
```

---

## Summary — All new env vars for `local.env`

```env
# --- Expand Data Sources (new) ---
GUARDIAN_API_KEY=
TAVILY_API_KEY=
CURRENTS_API_KEY=

# --- Optional model config (defaults to gpt-4.1 if unset) ---
ANALYSIS_MODEL=gpt-4.1
DIGEST_MODEL=gpt-4.1
```

> **Note**: All 3 API keys are optional — collectors gracefully skip sources when their key is missing. But for full functionality, all 3 should be set.

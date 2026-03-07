# Vercel Serverless Debugging

- **Always use `print()` for serverless log output** — Vercel captures stdout/stderr in function logs. Use `print(f"[MODULE] message")` with a bracketed prefix (e.g., `[DIGEST]`, `[TG /digest]`, `[INTERNAL/ANALYZE]`) so logs are filterable.
- **Log at key lifecycle points**: function entry, before/after external calls (DB, HTTP, LLM), branch decisions, and error paths. This is critical because serverless functions are stateless — you can't attach a debugger.
- **Include context in logs**: Always log relevant IDs (digest_id, user_id), status values, and timing info. Example: `print(f"[DIGEST] Phase 2: {len(items)} items loaded, calling LLM...")`.
- **Log before raising HTTPException**: Print the error context before raising so it appears in Vercel logs even if the client only sees the HTTP status.
- **Use Vercel MCP or `vercel logs`** to check function logs after deployment. Always check logs when debugging production issues before making code changes.
- **Keep `logger.error()` for structured logging** alongside `print()` — logger feeds into any log aggregation, print feeds into Vercel's function log viewer.
- **Traceback on errors**: In except blocks, always capture `traceback.format_exc()` and print it. Truncate to last 500 chars if storing in DB fields.

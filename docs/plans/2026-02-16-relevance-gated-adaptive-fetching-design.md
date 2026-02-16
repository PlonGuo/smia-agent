# Design: Relevance-Gated Adaptive Fetching

**Date**: 2026-02-16
**Status**: Approved

## Problem

When a user queries "plaud.ai" vs "plaud ai", fetched results may include unrelated posts (generic AI discussions, other products). Currently there is no hard relevance gate — the main agent is told to filter via system prompt, but irrelevant data still pollutes the analysis and affects quality.

## Solution

Add a batch LLM relevance filter between raw data fetching and the main analysis agent. If too many results are irrelevant (yield < 50%), refetch with a larger limit (2x) and re-filter. Cap at one retry.

## Architecture

```
User query: "plaud.ai"
       ↓
  fetch_reddit_tool / fetch_youtube_tool / fetch_amazon_tool
       ↓
  ┌─── Existing: raw fetch (limit=5) ──────────────┐
  │  posts = await fetch_reddit(query, limit=5)     │
  └─────────────────────────────────────────────────┘
       ↓
  ┌─── NEW: batch relevance filter ─────────────────┐
  │  gpt-4o-mini call with titles + snippets        │
  │  → returns [true, false, true, ...]             │
  │  yield = relevant_count / total                  │
  └─────────────────────────────────────────────────┘
       ↓
  yield >= 50%?  → return relevant items
  yield < 50%?   → refetch with limit=10
                    → re-filter
                    → return relevant items (ONE retry max)
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Filter model | gpt-4o-mini | Binary yes/no judgment, 10x cheaper than gpt-4o |
| Filter input | title + first 200 chars | Enough to judge relevance, saves tokens |
| Yield threshold | 50% | Below this = query likely too noisy |
| Refetch multiplier | 2x original limit | Balances coverage vs cost |
| Max retries | 1 | Avoids infinite loops |
| Failure mode | Graceful — return all items unfiltered | If filter LLM call fails, don't block the pipeline |
| Langfuse tracing | @observe on filter function | Track filter accuracy over time |

## New Function: `relevance_filter()`

Location: `api/services/tools.py`

```python
async def relevance_filter(
    query: str,
    items: list[dict],    # each has "title" + "body"/"content"/"description"
    source: str,
) -> tuple[list[dict], float]:
    """
    Batch LLM relevance check using gpt-4o-mini.
    Returns (relevant_items, yield_ratio).
    On failure, returns (all_items, 1.0) — fail-open.
    """
```

Prompt sends titles + first 200 chars of body/content. Model returns a JSON array of booleans.

## Modified Tool Functions

Each tool gets the same adaptive pattern:

```python
async def fetch_reddit_tool(ctx, query):
    INITIAL_LIMIT = 5
    posts = await fetch_reddit(query, limit=INITIAL_LIMIT)
    relevant, yield_ratio = await relevance_filter(query, posts, "reddit")

    if yield_ratio < 0.5 and len(posts) == INITIAL_LIMIT:
        posts = await fetch_reddit(query, limit=INITIAL_LIMIT * 2)
        relevant, yield_ratio = await relevance_filter(query, posts, "reddit")

    # format and return relevant posts (existing logic)
```

Same pattern for `fetch_youtube_tool` and `fetch_amazon_tool`.

## Files Changed

- `api/services/tools.py` — add `relevance_filter()`, modify all three tool functions
- No changes to `crawler.py`, `agent.py`, or `schemas.py`

## Cost Estimate

- ~5 items x ~50 tokens each = ~250 input tokens per filter call
- gpt-4o-mini at $0.15/1M input = ~$0.00004 per filter call
- Worst case (3 sources x 2 calls each) = ~$0.00024 per analysis — negligible

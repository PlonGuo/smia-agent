# CLAUDE.md - YARS (Yet Another Reddit Scraper)

## Project Overview

YARS is a lightweight Python Reddit scraper that uses Reddit's public `.json` API endpoints (no API keys required). It scrapes posts, comments, user data, and media using the `requests` module with random user-agent rotation.

## Project Structure

```
yars/
├── CLAUDE.md                    # This file - project guide
├── README.md                    # Project documentation
├── LICENSE
├── logo.svg
├── .gitignore
├── .pre-commit-config.yaml
├── uv.lock                     # UV package manager lock file
├── example/
│   └── example.py              # Usage examples and template
└── src/
    ├── README.md               # (Empty)
    ├── osint.py                # OSINT user analysis module
    ├── pyproject.toml          # Project config (deps: requests, pygments, flask, meta-ai-api)
    └── yars/
        ├── __init__.py         # Package init (empty)
        ├── agents.py           # 850+ browser user-agent strings
        ├── sessions.py         # Random user-agent session class
        ├── utils.py            # Display, download, export utilities
        └── yars.py             # Main YARS scraper class
```

## File Details

### `src/yars/yars.py` — Main Scraper Class

**Class `YARS`** — Core scraping engine with retry logic and proxy support.

| Method                                                                        | Purpose                                                                                                                                                                                                          |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `__init__(proxy, timeout, random_user_agent)`                                 | Initialize session with optional proxy, timeout (default 10s), and random user-agent. Configures retry strategy (5 retries, exponential backoff, retries on 429/5xx).                                            |
| `handle_search(url, params, after, before)`                                   | Generic paginated search handler. Makes GET request to Reddit JSON API, extracts post title/link/permalink/description from response. Returns list of result dicts.                                              |
| `search_reddit(query, limit, sort, time_filter, after, before)`               | Search all of Reddit. Endpoint: `https://www.reddit.com/search.json`. Supports sort options: `relevance`, `hot`, `top`, `new`, `comments`. Supports time filters: `all`, `year`, `month`, `week`, `day`, `hour`. |
| `search_subreddit(subreddit, query, limit, sort, time_filter, after, before)` | Search within a specific subreddit. Endpoint: `https://www.reddit.com/r/{subreddit}/search.json`. Same sort/time_filter options as `search_reddit`. Uses `restrict_sr=on`.                                       |
| `scrape_post_details(permalink)`                                              | Scrape full post data (title, body, all comments with nested replies). Endpoint: `https://www.reddit.com{permalink}.json`.                                                                                       |
| `_extract_comments(comments)`                                                 | (Private) Recursively extract comments and nested replies. Filters for `kind="t1"` (comments). Returns list of `{author, body, score, replies}`.                                                                 |
| `scrape_user_data(username, limit)`                                           | Fetch user's recent posts/comments with pagination. Endpoint: `https://www.reddit.com/user/{username}/.json`. Sleeps 1-2s between batches.                                                                       |
| `fetch_subreddit_posts(subreddit, limit, category, time_filter)`              | Fetch posts from subreddit or user profile. Categories: `hot`, `top`, `new`, `userhot`, `usertop`, `usernew`. Returns post metadata including images/thumbnails.                                                 |

**Search sort options:** `relevance` (default), `hot`, `top`, `new`, `comments`
**Search time filters:** `all` (default), `year`, `month`, `week`, `day`, `hour`

### `src/yars/sessions.py` — Session Management

**Class `RandomUserAgentSession(Session)`** — Extends `requests.Session`, injects a random User-Agent header on every request via `get_agent()`.

### `src/yars/agents.py` — User Agent Strings

- **`USER_AGENTS`**: Tuple of 850+ browser user-agent strings.
- **`get_agent()`**: Returns a random user-agent string.

### `src/yars/utils.py` — Utility Functions

| Function                                            | Purpose                                                                                   |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `display_results(results, title)`                   | Pretty-print results as colorized JSON using Pygments. Handles both list and dict inputs. |
| `download_image(image_url, output_folder, session)` | Download image to disk (default folder: `images/`). Streams in 8192-byte chunks.          |
| `export_to_json(data, filename)`                    | Export data to JSON file with 4-space indentation.                                        |
| `export_to_csv(data, filename)`                     | Export list of dicts to CSV file.                                                         |

### `example/example.py` — Usage Template

| Function                                                               | Purpose                                                                                                                                         |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `display_data(miner, subreddit_name, query, limit, sort, time_filter)` | Demonstrates search, post scraping, user data, subreddit posts, and image download. Dynamically scrapes post details for all search results.    |
| `scrape_search_data(query, limit, sort, time_filter, filename)`        | Searches Reddit, then scrapes full details (body + comments) for each result. Saves incrementally to a dynamic JSON file named after the query. |
| `save_to_json(data, filename)`                                         | Utility to write data to JSON file with indentation.                                                                                            |

### `src/osint.py` — OSINT Analysis (Standalone)

**Class `RedditUserAnalyzer`** — Analyzes a Reddit user's comment history using Meta AI.

| Method                              | Purpose                                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `__init__()`                        | Initialize YARS scraper and MetaAI client.                                                                    |
| `scrape_user_data(username, limit)` | Scrape user comments, format as `{subreddit} > {body}`.                                                       |
| `generate_ai_prompt()`              | Create AI analysis prompt with 5 categories (personality, interests, communication, social behavior, themes). |
| `analyze_user()`                    | Send prompt to Meta AI and return response.                                                                   |

## API Endpoints Used

| Endpoint                                                  | Used By                               |
| --------------------------------------------------------- | ------------------------------------- |
| `https://www.reddit.com/search.json`                      | `search_reddit()`                     |
| `https://www.reddit.com/r/{sub}/search.json`              | `search_subreddit()`                  |
| `https://www.reddit.com{permalink}.json`                  | `scrape_post_details()`               |
| `https://www.reddit.com/user/{user}/.json`                | `scrape_user_data()`                  |
| `https://www.reddit.com/r/{sub}/{category}.json`          | `fetch_subreddit_posts()`             |
| `https://www.reddit.com/user/{user}/submitted/{cat}.json` | `fetch_subreddit_posts()` (user mode) |

## Running

```bash
# From project root (not src/)
uv run example/example.py
```

## Key Design Decisions

- No Reddit API keys needed — uses public `.json` endpoints
- Random user-agent rotation to avoid detection
- Exponential backoff retry strategy for rate limiting (429) and server errors
- Pagination via Reddit's `after`/`before` tokens
- 1-2 second random sleep between batch requests to be polite

---

## Changelog

### Changes Made (2026-02-13)

#### 1. Enhanced `search_reddit()` with sort and time_filter parameters (`src/yars/yars.py`)

**Before:** `sort` was hardcoded to `"relevance"`, no time filter support.

**After:** Added `sort` parameter (validated: `relevance`, `hot`, `top`, `new`, `comments`) and `time_filter` parameter (validated: `all`, `year`, `month`, `week`, `day`, `hour`).

```python
# Before
search_reddit(query, limit=10, after=None, before=None)
# After
search_reddit(query, limit=10, sort="relevance", time_filter="all", after=None, before=None)
```

#### 2. Fixed `search_subreddit()` to actually use sort parameter (`src/yars/yars.py`)

**Before:** Had a `sort` parameter but ignored it, always using `"relevance"`.

**After:** Now properly passes the `sort` parameter to the API. Also added `time_filter` support with the same validation.

```python
# Before
search_subreddit(subreddit, query, limit=10, after=None, before=None, sort="relevance")
# After
search_subreddit(subreddit, query, limit=10, sort="relevance", time_filter="all", after=None, before=None)
```

#### 3. Added `permalink` field to `handle_search()` results (`src/yars/yars.py`)

**Before:** Only returned `title`, `link`, `description`.

**After:** Also returns `permalink` (raw path like `/r/sub/comments/id/title/`) so results can be directly passed to `scrape_post_details()` without URL parsing.

#### 4. Rewrote `example.py` to be a dynamic, reusable template (`example/example.py`)

**Before:** Hardcoded permalink (`/r/getdisciplined/...`), hardcoded username (`iamsecb`), hardcoded filename (`subreddit_data3.json`).

**After:**

- `display_data()` now accepts `query`, `sort`, and `time_filter` parameters. It dynamically scrapes post details for **all** search results using the `permalink` field from search results.
- `scrape_search_data()` replaces `scrape_subreddit_data()` — searches Reddit, scrapes full details for each result, and saves to a JSON file dynamically named after the query (e.g., `search_OpenAI_relevance_all.json`).
- All POST-section data is dynamically generated from actual search results instead of hardcoded values.

#### 5. Added parameter validation (`src/yars/yars.py`)

Added `VALID_SORT_OPTIONS` and `VALID_TIME_FILTERS` constants with `ValueError` raised on invalid values, matching Reddit's web interface options:

- **Sort:** `relevance`, `hot`, `top`, `new`, `comments` (Comment Count)
- **Time:** `all` (All time), `year` (Past year), `month` (Past month), `week` (Past week), `day` (Today), `hour` (Past hour)

# Testing Strategy

## Backend Testing (pytest + httpx)
- Use `pytest` as the test runner for all backend tests
- Use `httpx.AsyncClient` with FastAPI's `TestClient` for API endpoint testing
- Test files go in `api/tests/` mirroring the source structure (e.g., `api/tests/test_routes/test_analyze.py`)
- Run tests with: `cd api && uv run pytest -v`
- Write tests BEFORE or alongside each feature implementation
- Mock external services (OpenAI, Supabase, Crawl4AI) in unit tests
- Use fixtures for common test setup (auth headers, sample data)

## Frontend Testing (Playwright MCP)
- Use **Playwright MCP** for E2E UI testing after building frontend components
- **Sign-in credentials**: Read `TEST_EMAIL` and `TEST_PASSWORD` from `local.env` for authenticated Playwright testing
- Test workflow: start dev server (`pnpm dev`), then use Playwright MCP to interact with pages
- Key things to test with Playwright:
  - Page navigation and routing works correctly
  - Chakra UI components render properly (forms, buttons, cards)
  - Dark/light mode toggle works
  - Analysis flow: submit query -> progress indicator -> results display
  - Dashboard: report cards render, filtering/sorting works
  - Responsive layout at different viewport sizes
  - Auth flow: login/signup forms, protected route redirects
- Use `browser_snapshot` (accessibility tree) over screenshots for verifying content
- Use `browser_navigate` + `browser_click` + `browser_type` for interaction testing

## Integration Testing
- Test the full analysis pipeline: API request -> tool calls -> structured output -> database save
- Verify Langfuse traces are created for each analysis
- Test Supabase RLS policies work (user A cannot access user B's reports)

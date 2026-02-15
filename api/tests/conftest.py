"""Shared test fixtures for SmIA API tests."""

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Add api/ to Python path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Disable Langfuse during tests so @observe traces don't pollute the dashboard
os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
os.environ.pop("LANGFUSE_SECRET_KEY", None)
os.environ["LANGFUSE_ENABLED"] = "false"

from core.auth import AuthenticatedUser, get_current_user  # noqa: E402
from index import app  # noqa: E402

# A fake authenticated user for testing protected endpoints.
MOCK_USER = AuthenticatedUser(user_id="test-user-id-123", access_token="fake-jwt")


async def _override_get_current_user() -> AuthenticatedUser:
    return MOCK_USER


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """Async test client for FastAPI app (no auth)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def authed_client():
    """Async test client with auth dependency overridden."""
    app.dependency_overrides[get_current_user] = _override_get_current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


def make_trend_report_data(**overrides) -> dict:
    """Factory for valid TrendReport test data."""
    data = {
        "topic": "Test Topic",
        "sentiment": "Positive",
        "sentiment_score": 0.75,
        "summary": "A" * 50,  # min_length=50
        "key_insights": ["insight1", "insight2", "insight3"],
        "top_discussions": [
            {
                "title": "Discussion 1",
                "url": "https://reddit.com/r/test/1",
                "source": "reddit",
                "score": 100,
            }
        ],
        "keywords": ["word1", "word2", "word3", "word4", "word5"],
        "source_breakdown": {"reddit": 10, "youtube": 5},
    }
    data.update(overrides)
    return data

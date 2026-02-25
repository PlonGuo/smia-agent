"""Tests for GitHub trending collector."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def _make_github_response(repos=None, status_code=200):
    """Create a mock httpx response for GitHub Search API."""
    if repos is None:
        repos = [
            {
                "full_name": "openai/swarm",
                "html_url": "https://github.com/openai/swarm",
                "description": "Educational framework for multi-agent orchestration",
                "owner": {"login": "openai"},
                "created_at": "2026-02-24T10:00:00Z",
                "stargazers_count": 1500,
                "language": "Python",
            },
            {
                "full_name": "user/cool-llm",
                "html_url": "https://github.com/user/cool-llm",
                "description": None,  # no description
                "owner": {"login": "user"},
                "created_at": "2026-02-24T08:00:00Z",
                "stargazers_count": 50,
                "language": "TypeScript",
            },
        ]

    response = MagicMock()
    response.status_code = status_code
    response.raise_for_status = MagicMock()
    response.json.return_value = {"items": repos, "total_count": len(repos)}
    if status_code == 403:
        response.raise_for_status.side_effect = Exception("Rate limited")
    return response


class TestGithubCollector:
    @pytest.mark.asyncio
    async def test_returns_items(self):
        mock_response = _make_github_response()

        with patch("services.collectors.github_collector.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from services.collectors.github_collector import GithubCollector
            items = await GithubCollector().collect()

            assert len(items) == 2
            assert items[0].source == "github"
            assert items[0].title == "openai/swarm"
            assert "github.com" in items[0].url
            assert items[0].author == "openai"
            assert items[0].extra["stars"] == 1500

    @pytest.mark.asyncio
    async def test_no_description(self):
        mock_response = _make_github_response()

        with patch("services.collectors.github_collector.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from services.collectors.github_collector import GithubCollector
            items = await GithubCollector().collect()

            # Second repo has no description
            assert items[1].snippet == ""

    @pytest.mark.asyncio
    async def test_empty_results(self):
        mock_response = _make_github_response(repos=[])

        with patch("services.collectors.github_collector.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from services.collectors.github_collector import GithubCollector
            items = await GithubCollector().collect()
            assert items == []

    @pytest.mark.asyncio
    async def test_rate_limited(self):
        mock_response = _make_github_response(status_code=403)

        with patch("services.collectors.github_collector.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from services.collectors.github_collector import GithubCollector
            items = await GithubCollector().collect()
            assert items == []

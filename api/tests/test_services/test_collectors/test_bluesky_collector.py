"""Tests for Bluesky collector."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def _recent_iso() -> str:
    """Return an ISO timestamp 1 hour ago so it's always within the 48h window."""
    return (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_bsky_response(posts=None, status_code=200):
    """Create a mock httpx response for Bluesky AT Protocol API."""
    if posts is None:
        posts = [
            {
                "post": {
                    "uri": "at://did:plc:abc123/app.bsky.feed.post/xyz789",
                    "author": {
                        "did": "did:plc:abc123",
                        "handle": "researcher.bsky.social",
                    },
                    "record": {
                        "text": "Just published our new paper on efficient fine-tuning with LoRA improvements.",
                        "createdAt": _recent_iso(),
                    },
                    "embed": None,
                }
            }
        ]

    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {"feed": posts}
    return response


class TestBlueskyCollector:
    @pytest.mark.asyncio
    async def test_returns_items(self):
        mock_response = _make_bsky_response()

        with patch("services.collectors.bluesky_collector.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from services.collectors.bluesky_collector import BlueskyCollector
            items = await BlueskyCollector().collect()

            # Should have items from at least one handle
            assert len(items) > 0
            item = items[0]
            assert item.source == "bluesky"
            assert item.author == "researcher.bsky.social"
            assert "fine-tuning" in item.title

    @pytest.mark.asyncio
    async def test_empty_posts(self):
        mock_response = _make_bsky_response(posts=[])

        with patch("services.collectors.bluesky_collector.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from services.collectors.bluesky_collector import BlueskyCollector
            items = await BlueskyCollector().collect()
            assert items == []

    @pytest.mark.asyncio
    async def test_api_error_returns_empty(self):
        mock_response = _make_bsky_response(status_code=500)

        with patch("services.collectors.bluesky_collector.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from services.collectors.bluesky_collector import BlueskyCollector
            items = await BlueskyCollector().collect()
            assert items == []

    @pytest.mark.asyncio
    async def test_post_with_embedded_link(self):
        posts = [
            {
                "post": {
                    "uri": "at://did:plc:abc/app.bsky.feed.post/xyz",
                    "author": {"did": "did:plc:abc", "handle": "test.bsky.social"},
                    "record": {
                        "text": "Check out this paper",
                        "createdAt": _recent_iso(),
                    },
                    "embed": {
                        "$type": "app.bsky.embed.external#view",
                        "external": {
                            "uri": "https://arxiv.org/abs/2401.00001",
                            "title": "Important Paper",
                        },
                    },
                }
            }
        ]
        mock_response = _make_bsky_response(posts=posts)

        with patch("services.collectors.bluesky_collector.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from services.collectors.bluesky_collector import BlueskyCollector
            items = await BlueskyCollector().collect()

            # Should use embedded URL instead of bsky.app URL
            assert any("arxiv.org" in item.url for item in items)

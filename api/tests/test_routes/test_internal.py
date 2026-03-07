"""Tests for internal webhook endpoints."""

import pytest
from unittest.mock import patch, AsyncMock

from models.update_schemas import UpdateSummary


SAMPLE_COMMITS = [
    {"id": "abc1234567", "message": "feat: add new feature", "author": "dev", "url": "https://github.com/test/1"},
    {"id": "bcd2345678", "message": "fix: resolve bug", "author": "dev2", "url": "https://github.com/test/2"},
]

NOISE_COMMITS = [
    {"id": "ccc1111111", "message": "chore: bump deps", "author": "bot", "url": "#"},
    {"id": "ddd2222222", "message": "docs: update readme", "author": "dev", "url": "#"},
    {"id": "eee3333333", "message": "Merge pull request #5 from dev/feature", "author": "dev", "url": "#"},
]

MOCK_SUMMARY = UpdateSummary(
    headline="New feature and bug fix",
    summary="The platform received a new feature and a bug fix.",
    highlights=["Added a new feature", "Resolved a bug"],
)


class TestNotifyUpdate:
    @pytest.mark.anyio
    async def test_rejects_bad_secret(self, client):
        resp = await client.post(
            "/api/internal/notify-update",
            json={"commits": SAMPLE_COMMITS},
            headers={"x-internal-secret": "wrong-secret"},
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_skips_when_no_commits(self, client):
        with patch("routes.internal.settings") as mock_settings:
            mock_settings.internal_secret = "test-secret"
            resp = await client.post(
                "/api/internal/notify-update",
                json={"commits": []},
                headers={"x-internal-secret": "test-secret"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "skipped"

    @pytest.mark.anyio
    async def test_skips_when_no_users(self, client):
        with patch("routes.internal.settings") as mock_settings, \
             patch("routes.internal.get_all_user_emails", return_value=[]), \
             patch("routes.internal.summarize_commits", new_callable=AsyncMock, return_value=MOCK_SUMMARY):
            mock_settings.internal_secret = "test-secret"
            resp = await client.post(
                "/api/internal/notify-update",
                json={"commits": SAMPLE_COMMITS},
                headers={"x-internal-secret": "test-secret"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "skipped"
            assert resp.json()["reason"] == "no users found"

    @pytest.mark.anyio
    async def test_sends_emails_to_all_users(self, client):
        with patch("routes.internal.settings") as mock_settings, \
             patch("routes.internal.get_all_user_emails", return_value=["a@b.com", "c@d.com"]), \
             patch("routes.internal.summarize_commits", new_callable=AsyncMock, return_value=MOCK_SUMMARY), \
             patch("routes.internal.send_update_notification", return_value=2) as mock_send:
            mock_settings.internal_secret = "test-secret"
            resp = await client.post(
                "/api/internal/notify-update",
                json={"commits": SAMPLE_COMMITS},
                headers={"x-internal-secret": "test-secret"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["emails_sent"] == 2
            assert data["total_users"] == 2
            assert "elapsed_ms" in data
            mock_send.assert_called_once_with(MOCK_SUMMARY, ["a@b.com", "c@d.com"])

    @pytest.mark.anyio
    async def test_llm_fallback_on_failure(self, client):
        with patch("routes.internal.settings") as mock_settings, \
             patch("routes.internal.get_all_user_emails", return_value=["a@b.com"]), \
             patch("routes.internal.summarize_commits", new_callable=AsyncMock, side_effect=Exception("LLM down")), \
             patch("routes.internal.send_update_notification", return_value=1) as mock_send:
            mock_settings.internal_secret = "test-secret"
            resp = await client.post(
                "/api/internal/notify-update",
                json={"commits": SAMPLE_COMMITS},
                headers={"x-internal-secret": "test-secret"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"
            # Verify fallback summary was used
            call_args = mock_send.call_args[0]
            summary = call_args[0]
            assert isinstance(summary, UpdateSummary)
            assert "feat: add new feature" in summary.headline

    @pytest.mark.anyio
    async def test_invalid_body_returns_422(self, client):
        with patch("routes.internal.settings") as mock_settings:
            mock_settings.internal_secret = "test-secret"
            resp = await client.post(
                "/api/internal/notify-update",
                json={"bad_field": "bad_value"},
                headers={"x-internal-secret": "test-secret"},
            )
            assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_skips_when_all_noise_commits(self, client):
        with patch("routes.internal.settings") as mock_settings:
            mock_settings.internal_secret = "test-secret"
            resp = await client.post(
                "/api/internal/notify-update",
                json={"commits": NOISE_COMMITS},
                headers={"x-internal-secret": "test-secret"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "skipped"
            assert resp.json()["reason"] == "no meaningful commits"


class TestCommitFiltering:
    """Test the commit filtering logic in email_service."""

    def test_filters_noise_commits(self):
        from services.email_service import _filter_commits
        result = _filter_commits(NOISE_COMMITS)
        assert len(result) == 0

    def test_keeps_meaningful_commits(self):
        from services.email_service import _filter_commits
        result = _filter_commits(SAMPLE_COMMITS)
        assert len(result) == 2

    def test_mixed_commits(self):
        from services.email_service import _filter_commits
        mixed = SAMPLE_COMMITS + NOISE_COMMITS
        result = _filter_commits(mixed)
        assert len(result) == 2
        assert result[0]["id"] == "abc1234567"
        assert result[1]["id"] == "bcd2345678"

    def test_empty_commits(self):
        from services.email_service import _filter_commits
        assert _filter_commits([]) == []

    def test_all_noise_returns_empty(self):
        from services.email_service import _filter_commits
        result = _filter_commits([
            {"id": "x", "message": "ci: fix pipeline", "author": "bot", "url": "#"},
        ])
        assert len(result) == 0

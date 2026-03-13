"""Tests for core/langfuse_config.py."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestInitLangfuse:
    def test_init_langfuse_disabled_by_env(self):
        """LANGFUSE_ENABLED=false causes early return; _langfuse_enabled stays False."""
        import core.langfuse_config as lf_module

        # Ensure disabled flag is set (conftest may already set it, but be explicit)
        with patch.dict(os.environ, {"LANGFUSE_ENABLED": "false"}):
            lf_module._langfuse_enabled = False
            lf_module.init_langfuse()
            assert lf_module._langfuse_enabled is False

    def test_init_langfuse_sets_env_vars(self):
        """When keys are present and LANGFUSE_ENABLED is not 'false', env vars are set."""
        import core.langfuse_config as lf_module

        env_without_disabled = {k: v for k, v in os.environ.items() if k != "LANGFUSE_ENABLED"}

        mock_settings = MagicMock()
        mock_settings.langfuse_public_key = "pub-key-123"
        mock_settings.langfuse_secret_key = "sec-key-456"
        mock_settings.langfuse_base_url = "https://cloud.langfuse.com"

        with patch.dict(os.environ, env_without_disabled, clear=True), \
             patch("core.langfuse_config.settings", mock_settings), \
             patch("core.langfuse_config.Agent") as mock_agent:
            lf_module._langfuse_enabled = False
            lf_module.init_langfuse()
            assert os.environ.get("LANGFUSE_PUBLIC_KEY") == "pub-key-123"
            assert os.environ.get("LANGFUSE_SECRET_KEY") == "sec-key-456"
            assert lf_module._langfuse_enabled is True
            mock_agent.instrument_all.assert_called_once()

        # cleanup
        lf_module._langfuse_enabled = False

    def test_init_langfuse_missing_keys_logs_warning(self):
        """Empty Langfuse keys → warning logged, _langfuse_enabled stays False."""
        import core.langfuse_config as lf_module

        env_without_disabled = {k: v for k, v in os.environ.items() if k != "LANGFUSE_ENABLED"}

        mock_settings = MagicMock()
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.langfuse_base_url = "https://cloud.langfuse.com"

        with patch.dict(os.environ, env_without_disabled, clear=True), \
             patch("core.langfuse_config.settings", mock_settings):
            lf_module._langfuse_enabled = False
            lf_module.init_langfuse()
            assert lf_module._langfuse_enabled is False


class TestTraceMetadata:
    def test_trace_metadata_when_disabled(self):
        """_langfuse_enabled=False → returns without calling get_client()."""
        import core.langfuse_config as lf_module

        lf_module._langfuse_enabled = False
        with patch("core.langfuse_config.get_client") as mock_get_client:
            lf_module.trace_metadata(user_id="user-123")
            mock_get_client.assert_not_called()

    def test_trace_metadata_calls_update(self):
        """_langfuse_enabled=True → get_client() is called and update_current_trace invoked."""
        import core.langfuse_config as lf_module

        lf_module._langfuse_enabled = True
        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.environment = "test"

        with patch("core.langfuse_config.get_client", return_value=mock_client), \
             patch("core.langfuse_config.settings", mock_settings):
            lf_module.trace_metadata(user_id="user-123", session_id="sess-456")
            mock_client.update_current_trace.assert_called_once()
            call_kwargs = mock_client.update_current_trace.call_args[1]
            assert call_kwargs["user_id"] == "user-123"
            assert call_kwargs["session_id"] == "sess-456"

        # cleanup
        lf_module._langfuse_enabled = False


class TestFlushLangfuse:
    def test_flush_when_disabled(self):
        """_langfuse_enabled=False → no-op, get_client not called."""
        import core.langfuse_config as lf_module

        lf_module._langfuse_enabled = False
        with patch("core.langfuse_config.get_client") as mock_get_client:
            lf_module.flush_langfuse()
            mock_get_client.assert_not_called()

    def test_flush_calls_client(self):
        """_langfuse_enabled=True → get_client() called and flush() invoked."""
        import core.langfuse_config as lf_module

        lf_module._langfuse_enabled = True
        mock_client = MagicMock()

        with patch("core.langfuse_config.get_client", return_value=mock_client):
            lf_module.flush_langfuse()
            mock_client.flush.assert_called_once()

        # cleanup
        lf_module._langfuse_enabled = False

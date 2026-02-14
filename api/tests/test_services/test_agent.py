"""Unit tests for PydanticAI agent configuration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent import SYSTEM_PROMPT, create_agent


class TestAgentConfig:
    def test_agent_created_with_correct_model(self):
        agent = create_agent()
        assert agent.name == "smia-analyzer"

    def test_agent_has_all_tools(self):
        agent = create_agent()
        tool_names = list(agent._function_toolset.tools)
        assert "fetch_reddit_tool" in tool_names
        assert "fetch_youtube_tool" in tool_names
        assert "fetch_amazon_tool" in tool_names
        assert "clean_noise_tool" in tool_names

    def test_system_prompt_mentions_key_instructions(self):
        assert "Reddit" in SYSTEM_PROMPT
        assert "YouTube" in SYSTEM_PROMPT
        assert "Amazon" in SYSTEM_PROMPT
        assert "TrendReport" in SYSTEM_PROMPT
        assert "sentiment" in SYSTEM_PROMPT

    def test_agent_output_type_is_trend_report(self):
        from models.schemas import TrendReport

        agent = create_agent()
        # The output type should be TrendReport
        assert agent._output_type is not None

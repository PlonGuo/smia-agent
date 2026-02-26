"""Langfuse observability setup for SmIA (v3 API)."""

import logging
import os
from typing import Optional

from langfuse import get_client, observe
from pydantic_ai import Agent

from core.config import settings

logger = logging.getLogger(__name__)

_langfuse_enabled = False


def init_langfuse() -> None:
    """Initialize Langfuse by setting the required environment variables.

    Langfuse v3 reads from env vars automatically.  We set them from our
    settings so that ``@observe()`` decorators and ``get_client()`` work.

    If keys are not configured or LANGFUSE_ENABLED=false, Langfuse is
    disabled gracefully (no error).
    """
    global _langfuse_enabled

    # Allow explicitly disabling (e.g. during tests)
    if os.environ.get("LANGFUSE_ENABLED", "").lower() == "false":
        logger.info("Langfuse explicitly disabled via LANGFUSE_ENABLED=false")
        return

    if settings.langfuse_public_key and settings.langfuse_secret_key:
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
        os.environ["LANGFUSE_HOST"] = settings.langfuse_base_url
        _langfuse_enabled = True

        # Instrument all PydanticAI agents so LLM calls (model, tokens, cost)
        # are exported as OpenTelemetry spans and captured by Langfuse.
        Agent.instrument_all()
        logger.info("Langfuse enabled + PydanticAI agents instrumented")
    else:
        logger.warning(
            "Langfuse keys not configured — observability disabled. "
            "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable."
        )


def trace_metadata(
    user_id: str,
    session_id: Optional[str] = None,
    source: str = "web",
    tags: Optional[list[str]] = None,
) -> None:
    """Update the current Langfuse trace with user/session metadata."""
    if not _langfuse_enabled:
        return
    try:
        env = settings.environment
        trace_tags = list(tags or [])
        trace_tags.append(env)

        client = get_client()
        client.update_current_trace(
            user_id=user_id,
            session_id=session_id,
            tags=trace_tags,
            metadata={"source": source, "environment": env},
        )
    except Exception:
        pass


def flush_langfuse() -> None:
    """Flush pending Langfuse events so they are sent to the server."""
    if not _langfuse_enabled:
        return
    try:
        client = get_client()
        client.flush()
    except Exception:
        pass

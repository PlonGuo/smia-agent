"""Langfuse observability setup for SmIA (v3 API)."""

import os
from typing import Optional

from langfuse import get_client, observe

from core.config import settings


def init_langfuse() -> None:
    """Initialize Langfuse by setting the required environment variables.

    Langfuse v3 reads from env vars automatically.  We set them from our
    settings so that ``@observe()`` decorators and ``get_client()`` work.
    """
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
        os.environ["LANGFUSE_HOST"] = settings.langfuse_base_url
    else:
        raise ValueError(
            "Langfuse keys not configured. "
            "Please set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in local.env"
        )


def trace_metadata(
    user_id: str,
    session_id: Optional[str] = None,
    source: str = "web",
    tags: Optional[list[str]] = None,
) -> None:
    """Update the current Langfuse trace with user/session metadata."""
    client = get_client()
    client.update_current_trace(
        user_id=user_id,
        session_id=session_id,
        tags=tags or [],
        metadata={"source": source},
    )


def flush_langfuse() -> None:
    """Flush pending Langfuse events so they are sent to the server."""
    client = get_client()
    client.flush()

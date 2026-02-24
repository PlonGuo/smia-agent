import os
from pathlib import Path

from pydantic_settings import BaseSettings

# Find local.env from project root (parent of api/)
_env_file = Path(__file__).resolve().parent.parent.parent / "local.env"


def _detect_environment() -> str:
    """Detect runtime environment: production, preview, or development."""
    vercel_env = os.environ.get("VERCEL_ENV", "")
    if vercel_env:
        return vercel_env  # "production" or "preview"
    if os.environ.get("VERCEL"):
        return "vercel-dev"
    return "development"


class Settings(BaseSettings):
    # Database
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # AI Services
    openai_api_key: str = ""
    open_ai_api_key: str = ""  # Alternative name from local.env
    firecrawl_api_key: str = ""

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://us.cloud.langfuse.com"

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""

    # YouTube
    youtube_api_key: str = ""

    # Proxy (ScraperAPI)
    scraper_api_key: str = ""

    # Rate Limiting
    rate_limit_per_hour: int = 10

    # Email (Resend)
    resend_api_key: str = ""
    admin_email: str = ""  # Bootstrap only: seeds first admin

    # Bluesky (optional)
    bluesky_app_password: str = ""

    # Internal (two-phase pipeline trigger)
    internal_secret: str = "smia-internal-digest-trigger-key"
    app_url: str = ""  # Set in Vercel env, e.g. https://smia-agent.vercel.app

    # Environment (auto-detected)
    environment: str = ""

    @property
    def effective_openai_key(self) -> str:
        """Return whichever OpenAI key is set, stripped of whitespace."""
        return (self.openai_api_key or self.open_ai_api_key).strip()

    model_config = {"env_file": str(_env_file), "extra": "ignore"}


settings = Settings()
if not settings.environment:
    settings.environment = _detect_environment()

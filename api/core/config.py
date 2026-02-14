from pathlib import Path

from pydantic_settings import BaseSettings

# Find local.env from project root (parent of api/)
_env_file = Path(__file__).resolve().parent.parent.parent / "local.env"


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

    # Rate Limiting
    rate_limit_per_hour: int = 10

    @property
    def effective_openai_key(self) -> str:
        """Return whichever OpenAI key is set."""
        return self.openai_api_key or self.open_ai_api_key

    model_config = {"env_file": str(_env_file), "extra": "ignore"}


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # AI Services
    openai_api_key: str = ""
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

    model_config = {"env_file": "local.env", "extra": "ignore"}


settings = Settings()

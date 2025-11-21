import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore[misc]
    """Application configuration loaded from environment variables."""

    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db: str = "defra_agent"

    pg_dsn: str = "dbname=defra user=defra password=defra host=postgres"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    anomaly_threshold: float = 3.0

    public_registers_dist_km: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Ensure OPENAI_API_KEY is set in environment for OpenAI SDK
if settings.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore[misc]
    """Application configuration loaded from environment variables."""

    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db: str = "defra_agent"

    pg_dsn: str = "dbname=defra user=defra password=defra host=postgres"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    anomaly_threshold: float = 3.0

    public_registers_base_url: str = "https://environment.data.gov.uk/public-register"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

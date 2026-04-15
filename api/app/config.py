"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    database_url: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()

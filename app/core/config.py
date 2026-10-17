"""Application settings and environment configuration module.

Loads environment variables using Pydantic Settings, providing strongly-typed
access to database credentials, Redis message broker URLs, and Celery worker flags.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration settings loaded from environment variables or .env file."""

    PROJECT_NAME: str = "News Article Management & Summarization API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL Database Connection Strings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/simprosys_test"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/simprosys_test"

    # Redis and Celery Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.logging import configure_logging


class Settings(BaseSettings):
    DB_URL: str

    JWT_SECRET_KEY: str

    BOT_API_SECRET: str
    BOT_MESSAGE_MAX_AGE_SECONDS: int = 300

    GEMINI_API_KEY: str
    DEFAULT_AI_MODEL: str

    REDIS_URL: str
    REDIS_CONNECT_TIMEOUT: float = 1.0
    REDIS_SOCKET_TIMEOUT: float = 1.0
    REDIS_MAX_CONNECTIONS: int | None = None
    REDIS_HEALTH_CHECK_INTERVAL: int = 30

    CACHE_TTL: int = 300
    CACHE_METADATA_TTL: int = 3600

    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "backend"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    CHARACTER_GENERATION_DAILY_LIMIT: int = 5

    RABBITMQ_URL: str
    RABBITMQ_EXCHANGE: str
    RABBITMQ_QUEUE_PREFIX: str

    RABBITMQ_EXCHANGE_TYPE: str = "topic"
    RABBITMQ_PREFETCH_COUNT: int = 10
    RABBITMQ_RECONNECT_INTERVAL_SECONDS: float = 5.0
    RABBITMQ_MAX_RETRIES: int = 3
    RABBITMQ_RETRY_DELAY_SECONDS: float = 5.0

    model_config = SettingsConfigDict(
    env_file=Path(__file__).resolve().parents[2] / ".env",
    extra="ignore",
)

settings = Settings()

configure_logging(
    level=settings.LOG_LEVEL,
    service=settings.SERVICE_NAME,
    environment=settings.ENVIRONMENT,
    json_output=settings.LOG_JSON,
)
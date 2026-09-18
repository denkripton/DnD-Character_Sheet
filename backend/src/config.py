import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO)

CACHE_TTL = 300


class Settings(BaseSettings):
    DB_URL: str

    JWT_SECRET_KEY: str

    GEMINI_API_KEY: str
    DEFAULT_AI_MODEL: str

    REDIS_URL: str
    REDIS_CONNECT_TIMEOUT: float = 1.0
    REDIS_SOCKET_TIMEOUT: float = 1.0
    REDIS_MAX_CONNECTIONS: int | None = None
    REDIS_HEALTH_CHECK_INTERVAL: int = 30

    RABBITMQ_URL: str
    RABBITMQ_EXCHANGE: str
    RABBITMQ_QUEUE_PREFIX: str

    RABBITMQ_EXCHANGE_TYPE: str = "topic"
    RABBITMQ_PREFETCH_COUNT: int = 10
    RABBITMQ_RECONNECT_INTERVAL_SECONDS: float = 5.0

    model_config = SettingsConfigDict(
    env_file=Path(__file__).resolve().parents[2] / ".env",
    extra="ignore",
)

settings = Settings()
logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    BOT_TOKEN: str
    BOT_RABBITMQ_QUEUE_PREFIX: str = "bot"
    BOT_FSM_STORAGE: Literal["memory", "redis"] = "memory"

    LOG_LEVEL: str = "INFO"

    RABBITMQ_URL: str = "amqp://backend:backend@rabbitmq:5672/"
    RABBITMQ_EXCHANGE: str = "dnd.events"
    RABBITMQ_EXCHANGE_TYPE: str = "topic"
    RABBITMQ_PREFETCH_COUNT: int = 10
    RABBITMQ_RECONNECT_INTERVAL_SECONDS: float = 5.0
    RABBITMQ_MAX_RETRIES: int = 3
    RABBITMQ_RETRY_DELAY_SECONDS: float = 5.0

    REDIS_URL: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )


def load_config() -> BotConfig:
    return BotConfig()
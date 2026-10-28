from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    BOT_TOKEN: str
    BOT_RABBITMQ_QUEUE_PREFIX: str = "bot"
    BOT_FSM_STORAGE: Literal["memory", "redis"] = "memory"

    BACKEND_BASE_URL: str = "http://backend:8000"
    BOT_API_SECRET: str = ""
    BOT_MESSAGE_MAX_AGE_SECONDS: int = 300

    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "bot"
    LOG_JSON: bool = True
    MINI_APP_URL: str | None = None

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

    @field_validator("MINI_APP_URL")
    @classmethod
    def validate_mini_app_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("MINI_APP_URL must be an absolute HTTP(S) URL")
        return value

    @model_validator(mode="after")
    def require_https_mini_app_url_in_production(self):
        if (
            self.MINI_APP_URL
            and self.ENVIRONMENT.lower() == "production"
            and not self.MINI_APP_URL.lower().startswith("https://")
        ):
            raise ValueError("MINI_APP_URL must use HTTPS in production")
        return self


def load_config() -> BotConfig:
    return BotConfig()

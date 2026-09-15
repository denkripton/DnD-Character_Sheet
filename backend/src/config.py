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

    model_config = SettingsConfigDict(
    env_file=Path(__file__).resolve().parents[2] / ".env",
    extra="ignore",
)

settings = Settings()
logger = logging.getLogger(__name__)
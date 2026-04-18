import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    DB_URL: str

    JWT_SECRET_KEY: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
logger = logging.getLogger(__name__)
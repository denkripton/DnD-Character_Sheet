from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from app.config import BotConfig


def create_fsm_storage(config: BotConfig) -> BaseStorage:
    if config.BOT_FSM_STORAGE == "redis":
        return RedisStorage.from_url(config.REDIS_URL)
    return MemoryStorage()
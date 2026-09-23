import asyncio

from aiogram.fsm.storage.memory import MemoryStorage
from app.api import create_bot, create_dispatcher
from app.config import BotConfig
from app.main import close_storage


def test_create_dispatcher_uses_memory_storage():
    dispatcher = create_dispatcher(BotConfig(BOT_TOKEN="12345:test-token"))
    assert isinstance(dispatcher.storage, MemoryStorage)
    assert dispatcher["config"] is not None
    assert dispatcher["start_service"] is not None


def test_create_dispatcher_redis_storage():
    dispatcher = create_dispatcher(
        BotConfig(BOT_TOKEN="12345:test-token", BOT_FSM_STORAGE="redis"),
    )
    assert dispatcher.storage.__class__.__name__ == "RedisStorage"


def test_create_dispatcher_registers_start_router():
    dispatcher = create_dispatcher(BotConfig(BOT_TOKEN="12345:test-token"))
    assert "config" in dispatcher.workflow_data
    assert "start_service" in dispatcher.workflow_data


def test_create_bot_token():
    bot = create_bot(BotConfig(BOT_TOKEN="12345:test-token"))
    assert bot.token == "12345:test-token"
    assert bot.default.parse_mode is not None


def test_close_storage_sync_close():
    asyncio.run(close_storage(MemoryStorage()))
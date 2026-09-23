from app.config import BotConfig
from app.infrastructure.fsm.storage import create_fsm_storage


def test_memory_storage():
    storage = create_fsm_storage(BotConfig(BOT_TOKEN="12345:test-token", BOT_FSM_STORAGE="memory"))
    assert storage.__class__.__name__ == "MemoryStorage"


def test_redis_storage():
    storage = create_fsm_storage(BotConfig(BOT_TOKEN="12345:test-token", BOT_FSM_STORAGE="redis"))
    assert storage.__class__.__name__ == "RedisStorage"


def test_default_is_memory_storage():
    storage = create_fsm_storage(BotConfig(BOT_TOKEN="12345:test-token"))
    assert storage.__class__.__name__ == "MemoryStorage"
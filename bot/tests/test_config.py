from app.config import load_config


def test_defaults(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "12345:test-token")
    config = load_config()
    assert config.BOT_TOKEN == "12345:test-token"
    assert config.BOT_RABBITMQ_QUEUE_PREFIX == "bot"
    assert config.BOT_FSM_STORAGE == "memory"
    assert config.LOG_LEVEL == "INFO"
    assert config.RABBITMQ_EXCHANGE == "dnd.events"
    assert config.RABBITMQ_EXCHANGE_TYPE == "topic"
    assert config.RABBITMQ_PREFETCH_COUNT == 10
    assert config.RABBITMQ_RECONNECT_INTERVAL_SECONDS == 5.0
    assert config.RABBITMQ_MAX_RETRIES == 3
    assert config.RABBITMQ_RETRY_DELAY_SECONDS == 5.0


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "12345:test-token")
    monkeypatch.setenv("BOT_RABBITMQ_QUEUE_PREFIX", "assistant")
    monkeypatch.setenv("BOT_FSM_STORAGE", "redis")
    monkeypatch.setenv("RABBITMQ_PREFETCH_COUNT", "25")
    monkeypatch.setenv("RABBITMQ_MAX_RETRIES", "7")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:9999/3")
    config = load_config()
    assert config.BOT_RABBITMQ_QUEUE_PREFIX == "assistant"
    assert config.BOT_FSM_STORAGE == "redis"
    assert config.RABBITMQ_PREFETCH_COUNT == 25
    assert config.RABBITMQ_MAX_RETRIES == 7
    assert config.REDIS_URL == "redis://localhost:9999/3"
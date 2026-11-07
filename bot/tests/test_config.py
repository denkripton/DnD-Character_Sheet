from app.config import BotConfig, load_config


def test_defaults(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "12345:test-token")
    monkeypatch.setenv("BOT_API_SECRET", "")
    config = load_config()
    assert config.BOT_TOKEN == "12345:test-token"
    assert config.BOT_RABBITMQ_QUEUE_PREFIX == "bot"
    assert config.BOT_FSM_STORAGE == "memory"
    assert config.BACKEND_BASE_URL == "http://backend:8000"
    assert config.BOT_API_SECRET == ""
    assert config.BOT_MESSAGE_MAX_AGE_SECONDS == 300
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
    monkeypatch.setenv("BACKEND_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("BOT_API_SECRET", "secret-value")
    monkeypatch.setenv("BOT_MESSAGE_MAX_AGE_SECONDS", "60")
    monkeypatch.setenv("RABBITMQ_PREFETCH_COUNT", "25")
    monkeypatch.setenv("RABBITMQ_MAX_RETRIES", "7")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:9999/3")
    config = load_config()
    assert config.BOT_RABBITMQ_QUEUE_PREFIX == "assistant"
    assert config.BOT_FSM_STORAGE == "redis"
    assert config.BACKEND_BASE_URL == "http://localhost:8000"
    assert config.BOT_API_SECRET == "secret-value"
    assert config.BOT_MESSAGE_MAX_AGE_SECONDS == 60
    assert config.RABBITMQ_PREFETCH_COUNT == 25
    assert config.RABBITMQ_MAX_RETRIES == 7
    assert config.REDIS_URL == "redis://localhost:9999/3"


def test_mini_app_url_is_optional_and_allows_development_http(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "12345:test-token")
    monkeypatch.setenv("MINI_APP_URL", "http://localhost:5173")
    config = load_config()
    assert config.MINI_APP_URL == "http://localhost:5173"


def test_mini_app_url_requires_https_in_production(monkeypatch):
    import pytest
    from pydantic import ValidationError

    monkeypatch.setenv("BOT_TOKEN", "12345:test-token")
    with pytest.raises(ValidationError):
        BotConfig(
            BOT_TOKEN="12345:test-token",
            ENVIRONMENT="production",
            MINI_APP_URL="http://app.example.com",
        )


def test_mini_app_url_is_trimmed(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "12345:test-token")
    config = BotConfig(
        BOT_TOKEN="12345:test-token", MINI_APP_URL=" https://app.example.com/ "
    )

    assert config.MINI_APP_URL == "https://app.example.com/"


def test_mini_app_url_rejects_relative_url():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        BotConfig(BOT_TOKEN="12345:test-token", MINI_APP_URL="/mini-app")

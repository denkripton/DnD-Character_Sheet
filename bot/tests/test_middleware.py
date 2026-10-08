import asyncio
import json
from types import SimpleNamespace

import pytest
import structlog.contextvars
from app.middlewares.logging import LoggingMiddleware
from app.utils.logging import configure_logging


def _capturing_handler(captured):
    async def fake_handler(event, data):
        captured.update(structlog.contextvars.merge_contextvars(None, None, {}))
        return "ok"

    return fake_handler


def test_middleware_binds_user_context():
    middleware = LoggingMiddleware()
    event = SimpleNamespace(
        from_user=SimpleNamespace(id=42, username="hero", first_name="Hana"),
    )
    captured = {}
    handler = _capturing_handler(captured)

    async def scenario():
        return await middleware(handler, event, {})

    result = asyncio.run(scenario())
    assert result == "ok"
    assert captured["user_id"] == 42
    assert captured["username"] == "hero"
    assert captured["update_type"] == "SimpleNamespace"


def test_middleware_cleans_context_after_call():
    middleware = LoggingMiddleware()
    event = SimpleNamespace(from_user=SimpleNamespace(id=1, username="x", first_name=""))

    async def handler(event, data):
        return None

    async def scenario():
        await middleware(handler, event, {})
        return structlog.contextvars.merge_contextvars(None, None, {})

    merged = asyncio.run(scenario())
    assert "user_id" not in merged


def test_middleware_propagates_exception():
    middleware = LoggingMiddleware()
    event = SimpleNamespace(from_user=None)

    async def failing(event, data):
        raise RuntimeError("boom")

    async def scenario():
        await middleware(failing, event, {})
        raise AssertionError("expected RuntimeError")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(scenario())


def test_middleware_logs_update_failed_with_exception(capsys):
    configure_logging("INFO", service="bot", environment="test", json_output=True)
    middleware = LoggingMiddleware()
    event = SimpleNamespace(
        from_user=SimpleNamespace(id=9, username=None, first_name="Hana"),
    )

    async def failing(event, data):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(middleware(failing, event, {}))

    records = [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.strip()
    ]
    failed = next(r for r in records if r["event"] == "update_failed")
    assert failed["user_id"] == 9
    assert failed["update_type"] == "SimpleNamespace"
    assert "RuntimeError" in failed["exception"]
    assert "username" not in failed
    assert structlog.contextvars.get_contextvars() == {}
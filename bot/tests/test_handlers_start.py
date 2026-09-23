import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.modules.start.router import build_start_router, handle_start
from app.modules.start.service import StartService


def _message(**user_attrs):
    message = AsyncMock()
    message.from_user = SimpleNamespace(
        id=7,
        username="hero",
        first_name="Hana",
        **user_attrs,
    )
    return message


def test_start_replies_with_greeting():
    message = _message()
    asyncio.run(handle_start(message, StartService()))
    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert "hero" in text


def test_start_handles_missing_user():
    message = AsyncMock()
    message.from_user = None
    asyncio.run(handle_start(message, StartService()))
    message.answer.assert_awaited_once()


def test_start_router_registers_handler():
    router = build_start_router()
    assert len(router.message.handlers) == 1
    assert router.name == "start"
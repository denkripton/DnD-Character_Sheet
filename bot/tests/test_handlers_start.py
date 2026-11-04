import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.modules.auth import PROVIDER_TELEGRAM, BotAuthService
from app.modules.auth.schemas.context import AuthContext
from app.modules.start.router import build_start_router, handle_start
from app.modules.start.service import StartService
from app.config import BotConfig
from app.infrastructure.http.exceptions import BackendAuthError
from app.presentation.messages import AUTH_UNAVAILABLE_TEXT


def _message(**user_attrs):
    message = AsyncMock()
    message.from_user = SimpleNamespace(
        id=7,
        username="hero",
        first_name="Hana",
        **user_attrs,
    )
    return message


def _auth_service(**overrides):
    service = AsyncMock(spec=BotAuthService)
    service.authenticate.return_value = AuthContext(
        provider=PROVIDER_TELEGRAM,
        provider_user_id="7",
        user_id="user-1",
        username="hero",
        access_token="token",
    )
    for key, value in overrides.items():
        setattr(service, key, value)
    return service


def _state():
    state = AsyncMock()
    state.get_data.return_value = {}
    return state


def test_start_replies_with_greeting_after_auth():
    message = _message()
    auth_service = _auth_service()
    state = _state()
    asyncio.run(handle_start(message, StartService(), auth_service, state))

    auth_service.authenticate.assert_awaited_once()
    state.update_data.assert_awaited_once_with(
        auth={
            "provider": PROVIDER_TELEGRAM,
            "provider_user_id": "7",
            "user_id": "user-1",
            "username": "hero",
            "access_token": "token",
        }
    )
    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert "hero" in text


def test_start_handles_missing_user_without_auth():
    message = AsyncMock()
    message.from_user = None
    auth_service = _auth_service()
    state = _state()
    asyncio.run(handle_start(message, StartService(), auth_service, state))

    auth_service.authenticate.assert_not_awaited()
    state.update_data.assert_not_awaited()
    message.answer.assert_awaited_once()


def test_start_auth_failure_answers_unavailable():
    message = _message()
    auth_service = _auth_service()
    auth_service.authenticate.side_effect = BackendAuthError("backend down")
    state = _state()
    asyncio.run(handle_start(message, StartService(), auth_service, state))

    auth_service.authenticate.assert_awaited_once()
    state.update_data.assert_not_awaited()
    message.answer.assert_awaited_once_with(AUTH_UNAVAILABLE_TEXT)


def test_start_router_registers_handler():
    router = build_start_router()
    assert len(router.message.handlers) == 1
    assert router.name == "start"


def test_start_does_not_offer_http_web_app_button():
    message = _message()
    message.chat.type = "private"

    asyncio.run(
        handle_start(
            message,
            StartService(),
            _auth_service(),
            _state(),
            BotConfig(
                BOT_TOKEN="12345:test-token", MINI_APP_URL="http://localhost:5173"
            ),
        )
    )

    assert message.answer.await_args.kwargs["reply_markup"] is None

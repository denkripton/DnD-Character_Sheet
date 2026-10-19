import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock
from urllib.parse import urlencode

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.config import settings
from src.modules.auth.dependencies import get_external_auth_service
from src.modules.auth.router import user_router
from src.modules.auth.schemas.telegram_mini_app import TelegramMiniAppAuthRequest
from src.modules.auth.telegram_init_data import validate_telegram_init_data
from src.utils.exceptions import ServiceError
from src.utils.exceptions.handlers import service_error_handler

BOT_TOKEN = "test-bot-token"
NOW = 1_700_000_000


def _init_data(auth_date=NOW, user_id=42):
    values = {
        "auth_date": str(auth_date),
        "query_id": "query-1",
        "user": json.dumps({"id": user_id, "first_name": "Hero"}, separators=(",", ":")),
    }
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_valid_init_data_returns_verified_telegram_user():
    user = validate_telegram_init_data(_init_data(), BOT_TOKEN, now=NOW)

    assert user == {"id": 42, "first_name": "Hero"}


@pytest.mark.parametrize(
    "query",
    [
        _init_data(auth_date=NOW - 301),
        _init_data(auth_date=NOW + 1),
        _init_data().replace("query-1", "tampered"),
        _init_data() + "&auth_date=1700000000",
    ],
)
def test_invalid_stale_or_tampered_init_data_is_rejected(query):
    with pytest.raises(ServiceError) as exc_info:
        validate_telegram_init_data(query, BOT_TOKEN, now=NOW)

    assert exc_info.value.status_code == 401


def test_missing_bot_token_is_configuration_error():
    with pytest.raises(ServiceError) as exc_info:
        validate_telegram_init_data(_init_data(), None, now=NOW)

    assert exc_info.value.status_code == 503


def test_telegram_auth_route_maps_verified_identity_and_omits_refresh(monkeypatch):
    service = AsyncMock()
    service.authenticate_request.return_value = {
        "access": "access-jwt",
        "user": {"id": "00000000-0000-0000-0000-000000000001", "username": "telegram_42"},
    }
    app = FastAPI()
    app.include_router(user_router)
    app.dependency_overrides[get_external_auth_service] = lambda: service
    monkeypatch.setattr(settings, "BOT_TOKEN", BOT_TOKEN)
    monkeypatch.setattr(settings, "TELEGRAM_INIT_DATA_MAX_AGE_SECONDS", 300)
    init_data = _init_data(auth_date=int(time.time()))

    with TestClient(app) as client:
        response = client.post(
            "/users/auth/external",
            json={"init_data": init_data},
        )

    assert response.status_code == 200
    assert response.json() == {
        "access": "access-jwt",
        "user": {"id": "00000000-0000-0000-0000-000000000001", "username": "telegram_42"},
    }
    service.authenticate_request.assert_awaited_once_with(
        data=TelegramMiniAppAuthRequest(init_data=init_data),
        bot_secret=None,
    )


def test_external_auth_rejects_untrusted_external_identity_without_bot_secret():
    app = FastAPI()
    app.include_router(user_router)
    app.add_exception_handler(ServiceError, service_error_handler)

    with TestClient(app) as client:
        response = client.post(
            "/users/auth/external",
            json={"provider": "telegram", "provider_user_id": "42"},
        )

    assert response.status_code == 401

import asyncio
import uuid

import aiohttp
import pytest
from app.config import BotConfig
from app.infrastructure.http.client import (
    AUTH_BOT_SECRET_HEADER,
    EXTERNAL_AUTH_PATH,
    BackendApiClient,
)
from app.utils.exceptions import BackendAuthError


def _config(**overrides):
    return BotConfig(BOT_TOKEN="12345:test-token", **overrides)


class _Posted:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    async def __aenter__(self):
        if self._error is not None:
            raise self._error
        return self._response

    async def __aexit__(self, *args):
        return False


class FakeResponse:
    def __init__(self, status, data):
        self.status = status
        self._data = data

    async def json(self):
        return self._data


class FakeSession:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.requests = []

    def post(self, url, *, json=None, headers=None):
        self.requests.append((url, json, headers))
        return _Posted(response=self._response, error=self._error)


def _auth_payload():
    return {
        "access": "access-token",
        "refresh": "refresh-token",
        "user": {
            "id": str(uuid.uuid4()),
            "username": "telegram_7",
        },
    }


def test_client_posts_to_external_auth_endpoint():
    session = FakeSession(response=FakeResponse(200, _auth_payload()))
    client = BackendApiClient(_config(BOT_API_SECRET="secret"), session=session)

    result = asyncio.run(client.authenticate_external("telegram", "7"))

    assert result.access == "access-token"
    assert result.user.username == "telegram_7"
    (url, body, headers), = session.requests
    assert url == f"http://backend:8000{EXTERNAL_AUTH_PATH}"
    assert body == {"provider": "telegram", "provider_user_id": "7"}
    assert headers == {AUTH_BOT_SECRET_HEADER: "secret"}


def test_client_uses_configured_base_url():
    session = FakeSession(response=FakeResponse(200, _auth_payload()))
    client = BackendApiClient(
        _config(BACKEND_BASE_URL="http://localhost:9999", BOT_API_SECRET="secret"),
        session=session,
    )

    asyncio.run(client.authenticate_external("telegram", "7"))

    (url, _, _), = session.requests
    assert url == f"http://localhost:9999{EXTERNAL_AUTH_PATH}"


def test_client_raises_on_error_status():
    session = FakeSession(response=FakeResponse(401, {"detail": "nope"}))
    client = BackendApiClient(_config(BOT_API_SECRET="secret"), session=session)

    with pytest.raises(BackendAuthError):
        asyncio.run(client.authenticate_external("telegram", "7"))


def test_client_raises_on_connection_error():
    session = FakeSession(error=aiohttp.ClientConnectionError("down"))
    client = BackendApiClient(_config(BOT_API_SECRET="secret"), session=session)

    with pytest.raises(BackendAuthError):
        asyncio.run(client.authenticate_external("telegram", "7"))


def test_client_raises_on_invalid_response_body():
    session = FakeSession(response=FakeResponse(200, {"unexpected": True}))
    client = BackendApiClient(_config(BOT_API_SECRET="secret"), session=session)

    with pytest.raises(BackendAuthError):
        asyncio.run(client.authenticate_external("telegram", "7"))


def test_client_raises_when_secret_unconfigured():
    session = FakeSession()
    client = BackendApiClient(_config(BOT_API_SECRET=""), session=session)

    with pytest.raises(BackendAuthError):
        asyncio.run(client.authenticate_external("telegram", "7"))

    assert session.requests == []
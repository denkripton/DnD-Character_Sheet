import asyncio
import uuid

import pytest
from app.infrastructure.http.dto import ExternalAuthResponse
from app.modules.auth import PROVIDER_TELEGRAM, BotAuthService
from app.utils.exceptions import BackendAuthError


class FakeBackend:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def authenticate_external(self, provider, provider_user_id):
        self.calls.append((provider, provider_user_id))
        if self.error is not None:
            raise self.error
        return self.response


def _response():
    return ExternalAuthResponse(
        access="access-token",
        refresh="refresh-token",
        user={
            "id": uuid.uuid4(),
            "username": "telegram_7",
        },
    )


def test_authenticate_maps_backend_response_to_context():
    backend = FakeBackend(response=_response())
    service = BotAuthService(backend)

    context = asyncio.run(service.authenticate(7))

    assert backend.calls == [(PROVIDER_TELEGRAM, "7")]
    assert context.provider == PROVIDER_TELEGRAM
    assert context.provider_user_id == "7"
    assert context.username == "telegram_7"
    assert context.access_token == "access-token"


def test_authenticate_rejects_non_positive_id():
    service = BotAuthService(FakeBackend())

    with pytest.raises(BackendAuthError):
        asyncio.run(service.authenticate(0))


def test_authenticate_propagates_backend_error():
    backend = FakeBackend(error=BackendAuthError("backend down"))
    service = BotAuthService(backend)

    with pytest.raises(BackendAuthError):
        asyncio.run(service.authenticate(7))
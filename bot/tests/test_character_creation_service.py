import asyncio
from types import SimpleNamespace

import pytest
from app.messaging import MessageType
from app.modules.character.service import (
    FALLBACK_ERROR_TEXT,
    BackendUnavailableError,
    CharacterCreationError,
    CharacterCreationService,
)

AUTH = {
    "provider": "telegram",
    "provider_user_id": "7",
    "user_id": "user-1",
    "username": "hero",
    "access_token": "token",
}


class FakeRabbit:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []

    async def request(self, message_type, payload=None, **kwargs):
        self.calls.append(
            {"message_type": message_type, "payload": payload, "kwargs": kwargs}
        )
        if self.error is not None:
            raise self.error
        return SimpleNamespace(payload=self.payload)


def _service(payload=None, error=None):
    rabbit = FakeRabbit(payload=payload, error=error)
    return CharacterCreationService(rabbit), rabbit


def test_start_sends_create_command_with_identity():
    service, rabbit = _service(payload={"ok": True, "draft": {"id": "d1", "data": {}}})

    draft = asyncio.run(service.start(AUTH))

    assert draft == {"id": "d1", "data": {}}
    call = rabbit.calls[0]
    assert call["message_type"] == MessageType.CHARACTER_CREATE
    assert call["payload"] == {}
    assert call["kwargs"]["provider"] == "telegram"
    assert call["kwargs"]["provider_user_id"] == "7"
    assert call["kwargs"]["user_id"] == "user-1"


def test_set_value_sends_update_parameter_command():
    service, rabbit = _service(payload={"ok": True, "draft": {"id": "d1", "data": {}}})

    draft = asyncio.run(service.set_value(AUTH, "d1", "name", "Aria"))

    assert draft["id"] == "d1"
    call = rabbit.calls[0]
    assert call["message_type"] == MessageType.CHARACTER_UPDATE_PARAMETER
    assert call["payload"] == {
        "draft_id": "d1",
        "parameter": "name",
        "value": "Aria",
    }
    assert call["kwargs"]["user_id"] == "user-1"


def test_generate_value_sends_generate_flag():
    service, rabbit = _service(payload={"ok": True, "draft": {"id": "d1", "data": {}}})

    asyncio.run(service.generate_value(AUTH, "d1", "kind"))

    call = rabbit.calls[0]
    assert call["message_type"] == MessageType.CHARACTER_UPDATE_PARAMETER
    assert call["payload"] == {
        "draft_id": "d1",
        "parameter": "kind",
        "generate": True,
    }
    assert "value" not in call["payload"]


def test_cancel_sends_delete_command():
    service, rabbit = _service(payload={"ok": True})

    asyncio.run(service.cancel(AUTH, "d1"))

    call = rabbit.calls[0]
    assert call["message_type"] == MessageType.CHARACTER_DELETE
    assert call["payload"] == {"draft_id": "d1"}


def test_backend_rejection_raises_character_creation_error():
    service, _ = _service(payload={"ok": False, "error": "Name cannot be empty."})

    with pytest.raises(CharacterCreationError) as exc_info:
        asyncio.run(service.set_value(AUTH, "d1", "name", "x"))
    assert str(exc_info.value) == "Name cannot be empty."


def test_backend_rejection_without_message_uses_fallback():
    service, _ = _service(payload={"ok": False})

    with pytest.raises(CharacterCreationError) as exc_info:
        asyncio.run(service.start(AUTH))
    assert str(exc_info.value) == FALLBACK_ERROR_TEXT


def test_transport_failure_raises_backend_unavailable():
    service, _ = _service(error=ConnectionError("broker down"))

    with pytest.raises(BackendUnavailableError):
        asyncio.run(service.start(AUTH))


def test_timeout_raises_backend_unavailable():
    class TimeoutRabbit:
        async def request(self, *args, **kwargs):
            raise TimeoutError()

    service = CharacterCreationService(TimeoutRabbit())

    with pytest.raises(BackendUnavailableError):
        asyncio.run(service.start(AUTH))


def test_malformed_payload_raises_character_creation_error():
    service, _ = _service(payload="not-a-dict")

    with pytest.raises(CharacterCreationError):
        asyncio.run(service.start(AUTH))


def test_response_without_draft_raises_character_creation_error():
    service, _ = _service(payload={"ok": True})

    with pytest.raises(CharacterCreationError):
        asyncio.run(service.start(AUTH))

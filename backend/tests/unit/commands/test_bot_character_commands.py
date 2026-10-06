import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.messaging.contract import create_message
from src.messaging.enums import MessageType
from src.messaging.enums.constants import (
    AUTH_PROVIDER_HEADER,
    AUTH_PROVIDER_USER_ID_HEADER,
    AUTH_USER_ID_HEADER,
)
from src.modules.character.draft import CharacterDraftService
from src.modules.character.models import CharacterDraft
from src.modules.character.utils.random_character import KINDS
from src.modules.commands.dispatcher_factory import build_bot_command_dispatcher
from src.utils.exceptions import MessageAuthenticationError
from tests.utils import FakeRepo, FakeUnitOfWork


class DummyUser:
    def __init__(self, id):
        self.id = id


def _environment():
    user_repo = FakeRepo(model=DummyUser)
    user_repo.rows.append(DummyUser("user-1"))
    user_repo.rows.append(DummyUser("user-2"))
    draft_repo = FakeRepo(model=CharacterDraft)
    uow = FakeUnitOfWork()
    service = CharacterDraftService(
        draft_repository=draft_repo,
        user_repository=user_repo,
        unit_of_work=uow,
    )

    @asynccontextmanager
    async def scope():
        yield service

    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(
        producer, draft_service_scope=scope
    )
    return dispatcher, producer, draft_repo


def _headers(user_id="user-1"):
    return {
        AUTH_PROVIDER_HEADER: "telegram",
        AUTH_PROVIDER_USER_ID_HEADER: "7",
        AUTH_USER_ID_HEADER: user_id,
    }


def _command(message_type, payload=None, headers=None, correlation_id=None):
    return create_message(
        message_type,
        payload or {},
        correlation_id=correlation_id or uuid4(),
        headers=headers if headers is not None else _headers(),
    )


def _published(producer):
    event, routing_key = producer.publish.await_args.args
    return event, routing_key


def _create_draft(dispatcher, producer):
    correlation_id = uuid4()
    command = _command(MessageType.CHARACTER_CREATE, correlation_id=correlation_id)
    asyncio.run(dispatcher.handle(command))
    event, _ = _published(producer)
    assert event.type == MessageType.CHARACTER_CREATED.value
    assert event.correlation_id == correlation_id
    return event.payload["draft"]["id"]


def test_character_create_command_creates_draft():
    dispatcher, producer, draft_repo = _environment()
    correlation_id = uuid4()

    command = _command(MessageType.CHARACTER_CREATE, correlation_id=correlation_id)
    asyncio.run(dispatcher.handle(command))

    event, routing_key = _published(producer)
    assert event.type == MessageType.CHARACTER_CREATED.value
    assert routing_key == "events.character.created"
    assert event.correlation_id == correlation_id
    assert event.payload["ok"] is True
    assert event.payload["draft"]["data"] == {}
    assert len(draft_repo.rows) == 1
    assert draft_repo.rows[0].owner_id == "user-1"


def test_character_create_requires_identity_headers():
    dispatcher, producer, draft_repo = _environment()
    command = _command(MessageType.CHARACTER_CREATE, headers={})

    with pytest.raises(MessageAuthenticationError):
        asyncio.run(dispatcher.handle(command))
    assert draft_repo.rows == []
    producer.publish.assert_not_awaited()


def test_character_create_unknown_user_publishes_error():
    dispatcher, producer, _ = _environment()
    command = _command(MessageType.CHARACTER_CREATE, headers=_headers("ghost"))
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload == {"ok": False, "error": "User does not exist"}


def test_character_update_manual_parameter():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_UPDATE_PARAMETER,
        {"draft_id": draft_id, "parameter": "name", "value": "Aria"},
    )
    asyncio.run(dispatcher.handle(command))

    event, routing_key = _published(producer)
    assert event.type == MessageType.CHARACTER_UPDATED.value
    assert routing_key == "events.character.updated"
    assert event.payload["ok"] is True
    assert event.payload["draft"]["data"] == {"name": "Aria"}
    assert draft_repo.rows[0].data == {"name": "Aria"}


def test_character_update_generated_parameter():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_UPDATE_PARAMETER,
        {"draft_id": draft_id, "parameter": "kind", "generate": True},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is True
    assert event.payload["draft"]["data"]["kind"] in KINDS
    assert draft_repo.rows[0].data["kind"] in KINDS


def test_character_update_validation_error_is_friendly():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_UPDATE_PARAMETER,
        {"draft_id": draft_id, "parameter": "name", "value": "x" * 150},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert event.payload["error"] == "Name must be no more than 100 characters."


def test_character_update_other_user_draft_rejected():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_UPDATE_PARAMETER,
        {"draft_id": draft_id, "parameter": "name", "value": "Intruder"},
        headers=_headers("user-2"),
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert "not found" in event.payload["error"]


def test_character_update_invalid_payload_rejected():
    dispatcher, producer, _ = _environment()
    command = _command(
        MessageType.CHARACTER_UPDATE_PARAMETER,
        {"parameter": "name", "value": "Aria"},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload == {
        "ok": False,
        "error": "Invalid character draft update request.",
    }


def test_character_update_unknown_parameter_rejected():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_UPDATE_PARAMETER,
        {"draft_id": draft_id, "parameter": "luck", "value": "high"},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert event.payload["error"] == "Unsupported parameter: luck."


def test_character_delete_command_removes_draft():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_DELETE, {"draft_id": draft_id}
    )
    asyncio.run(dispatcher.handle(command))

    event, routing_key = _published(producer)
    assert event.type == MessageType.CHARACTER_DELETED.value
    assert routing_key == "events.character.deleted"
    assert event.payload == {"ok": True}
    assert draft_repo.rows == []


def test_character_delete_other_user_draft_rejected():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_DELETE,
        {"draft_id": draft_id},
        headers=_headers("user-2"),
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert len(draft_repo.rows) == 1


def test_sequential_flow_via_commands():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    steps = [
        ("name", "Aria"),
        ("kind", "Elf"),
        ("spec_class", "Wizard"),
    ]
    for parameter, value in steps:
        command = _command(
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "value": value},
        )
        asyncio.run(dispatcher.handle(command))
        event, _ = _published(producer)
        assert event.payload["ok"] is True

    assert draft_repo.rows[0].data == {
        "name": "Aria",
        "kind": "Elf",
        "spec_class": "Wizard",
    }


def test_signed_command_with_secret_verifies_and_dispatches():
    from src.messaging.security import sign_command

    secret = "shared-secret"
    user_repo = FakeRepo(model=DummyUser)
    user_repo.rows.append(DummyUser("user-1"))
    draft_repo = FakeRepo(model=CharacterDraft)

    @asynccontextmanager
    async def scope():
        yield CharacterDraftService(
            draft_repository=draft_repo,
            user_repository=user_repo,
            unit_of_work=FakeUnitOfWork(),
        )

    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(
        producer, secret=secret, draft_service_scope=scope
    )
    command = sign_command(
        _command(MessageType.CHARACTER_CREATE, headers=_headers()), secret
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is True


def test_unsigned_command_with_secret_rejected():
    secret = "shared-secret"
    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(producer, secret=secret)
    command = _command(MessageType.CHARACTER_CREATE)

    with pytest.raises(MessageAuthenticationError):
        asyncio.run(dispatcher.handle(command))

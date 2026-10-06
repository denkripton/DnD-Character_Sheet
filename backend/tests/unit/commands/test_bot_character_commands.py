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


STANDARD_VALUES = ["15", "14", "13", "12", "10", "8"]
STANDARD_STATS = {
    "strength": 15,
    "dexterity": 14,
    "constitution": 13,
    "intelligence": 12,
    "wisdom": 10,
    "charisma": 8,
}
STANDARD_MODIFIERS = {
    "strength": 2,
    "dexterity": 2,
    "constitution": 1,
    "intelligence": 1,
    "wisdom": 0,
    "charisma": -1,
}


def test_character_stats_generate_command_persists_stats():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "method": "standard"},
    )
    asyncio.run(dispatcher.handle(command))

    event, routing_key = _published(producer)
    assert event.type == MessageType.CHARACTER_STATS_CHANGED.value
    assert routing_key == "events.character.stats_changed"
    assert event.payload["ok"] is True
    assert event.payload["stats"] == STANDARD_STATS
    assert event.payload["modifiers"] == STANDARD_MODIFIERS
    assert draft_repo.rows[0].data["stats"] == STANDARD_STATS


def test_character_stats_generate_random_returns_domain_values():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "method": "random"},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is True
    stats = event.payload["stats"]
    modifiers = event.payload["modifiers"]
    assert set(stats) == {
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    }
    for value in stats.values():
        assert 3 <= value <= 18
    assert modifiers["strength"] == (stats["strength"] - 10) // 2
    assert draft_repo.rows[0].data["stats"] == stats


def test_character_stats_set_command_persists_manual_values():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "values": STANDARD_VALUES},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.type == MessageType.CHARACTER_STATS_CHANGED.value
    assert event.payload["ok"] is True
    assert event.payload["stats"] == STANDARD_STATS
    assert event.payload["modifiers"] == STANDARD_MODIFIERS
    assert draft_repo.rows[0].data["stats"] == STANDARD_STATS


def test_character_stats_set_validation_error_is_friendly():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "values": ["15", "15", "15", "10", "8", "8"]},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert (
        event.payload["error"]
        == "You must spend exactly 27 points! Spent: 29/27."
    )


def test_character_stats_missing_draft_id_rejected():
    dispatcher, producer, _ = _environment()
    command = _command(
        MessageType.CHARACTER_STATS, {"method": "standard"}
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload == {
        "ok": False,
        "error": "Invalid character stats request.",
    }


def test_character_stats_without_method_or_values_rejected():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)
    command = _command(MessageType.CHARACTER_STATS, {"draft_id": draft_id})
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload == {
        "ok": False,
        "error": "Invalid character stats request.",
    }


def test_character_stats_unknown_method_rejected():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "method": "luck"},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert event.payload["error"] == "Unsupported stats generation method: luck."


def test_character_stats_other_user_draft_rejected():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "values": STANDARD_VALUES},
        headers=_headers("user-2"),
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert "not found" in event.payload["error"]


def test_character_stats_requires_identity_headers():
    dispatcher, producer, draft_repo = _environment()
    command = _command(MessageType.CHARACTER_STATS, headers={})

    with pytest.raises(MessageAuthenticationError):
        asyncio.run(dispatcher.handle(command))
    assert draft_repo.rows == []
    producer.publish.assert_not_awaited()


def test_full_wizard_flow_via_commands():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    for parameter, value in [
        ("name", "Aria"),
        ("kind", "Elf"),
        ("spec_class", "Wizard"),
    ]:
        command = _command(
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "value": value},
        )
        asyncio.run(dispatcher.handle(command))
        event, _ = _published(producer)
        assert event.payload["ok"] is True

    command = _command(
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "method": "standard"},
    )
    asyncio.run(dispatcher.handle(command))
    event, _ = _published(producer)
    assert event.payload["ok"] is True

    data = draft_repo.rows[0].data
    assert data["name"] == "Aria"
    assert data["kind"] == "Elf"
    assert data["spec_class"] == "Wizard"
    assert data["stats"] == STANDARD_STATS

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError
from src.config import settings
from src.messaging.contract import create_message
from src.messaging.enums import MessageType
from src.messaging.enums.constants import (
    AUTH_PROVIDER_HEADER,
    AUTH_PROVIDER_USER_ID_HEADER,
    AUTH_USER_ID_HEADER,
)
from src.modules.character.base.enums.generation_limits import GenerationLimits
from src.modules.character.draft import CharacterDraftService
from src.modules.character.models import Character, CharacterDraft, Stat
from src.modules.character.utils.random_character import KINDS, NAMES, SPEC_CLASSES
from src.modules.commands.dispatcher_factory import build_bot_command_dispatcher
from src.utils.exceptions import MessageAuthenticationError
from src.utils.interfaces.rate_limiter import RateLimitResult
from tests.utils import FakeRepo, FakeUnitOfWork, StubRateLimiter


class DummyUser:
    def __init__(self, id):
        self.id = id


class RecordingRateLimiter:
    def __init__(self, allowed: bool = True):
        self.allowed = allowed
        self.calls = []

    async def is_limited(self, user_id, category, max_requests, time_window):
        self.calls.append((user_id, category, max_requests, time_window))
        if self.allowed:
            return RateLimitResult(
                allowed=True,
                current_usage=0,
                max_allowed=max_requests,
                remaining=max_requests,
                retry_after=0,
            )
        return RateLimitResult(
            allowed=False,
            current_usage=max_requests,
            max_allowed=max_requests,
            remaining=0,
            retry_after=time_window,
        )


class FlakyUnitOfWork(FakeUnitOfWork):
    def __init__(self, fail_after: int = 1):
        super().__init__()
        self.fail_after = fail_after

    async def commit(self):
        if self.commit_calls >= self.fail_after:
            raise OperationalError(
                "INSERT", {}, Exception("database is down")
            )
        await super().commit()


def _environment(rate_limiter=None, uow=None):
    user_repo = FakeRepo(model=DummyUser)
    user_repo.rows.append(DummyUser("user-1"))
    user_repo.rows.append(DummyUser("user-2"))
    draft_repo = FakeRepo(model=CharacterDraft)
    character_repo = FakeRepo(model=Character)
    stats_repo = FakeRepo(model=Stat)
    uow = uow or FakeUnitOfWork()
    service = CharacterDraftService(
        draft_repository=draft_repo,
        character_repository=character_repo,
        stats_repository=stats_repo,
        user_repository=user_repo,
        unit_of_work=uow,
        rate_limiter=rate_limiter or StubRateLimiter(allowed=True),
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
            character_repository=FakeRepo(model=Character),
            stats_repository=FakeRepo(model=Stat),
            user_repository=user_repo,
            unit_of_work=FakeUnitOfWork(),
            rate_limiter=StubRateLimiter(allowed=True),
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


def test_character_generate_command_creates_full_character():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)
    correlation_id = uuid4()

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id, "method": "standard"},
        correlation_id=correlation_id,
    )
    asyncio.run(dispatcher.handle(command))

    event, routing_key = _published(producer)
    assert event.type == MessageType.CHARACTER_GENERATED.value
    assert routing_key == "events.character.generated"
    assert event.correlation_id == correlation_id
    assert event.payload["ok"] is True
    assert event.payload["draft"]["data"]["name"] in NAMES
    assert event.payload["draft"]["data"]["kind"] in KINDS
    assert event.payload["draft"]["data"]["spec_class"] in SPEC_CLASSES
    assert event.payload["stats"] == STANDARD_STATS
    assert event.payload["modifiers"] == STANDARD_MODIFIERS
    assert draft_repo.rows[0].data["name"] in NAMES
    assert draft_repo.rows[0].data["stats"] == STANDARD_STATS


def test_character_generate_rate_limited():
    limiter = RecordingRateLimiter(allowed=False)
    dispatcher, producer, draft_repo = _environment(rate_limiter=limiter)
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id, "method": "standard"},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert "Daily limit reached" in event.payload["error"]
    assert draft_repo.rows[0].data == {}


def test_character_generate_regeneration_counts_against_limit():
    limiter = RecordingRateLimiter(allowed=True)
    dispatcher, producer, _ = _environment(rate_limiter=limiter)
    draft_id = _create_draft(dispatcher, producer)

    assert limiter.calls == []

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id, "method": "standard"},
    )
    asyncio.run(dispatcher.handle(command))
    event, _ = _published(producer)
    assert event.payload["ok"] is True
    assert len(limiter.calls) == 1
    assert limiter.calls[0] == (
        "user-1",
        GenerationLimits.KEY_PREFIX.value,
        settings.CHARACTER_GENERATION_DAILY_LIMIT,
        GenerationLimits.DAILY_WINDOW_SECONDS.value,
    )

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id, "method": "standard"},
    )
    asyncio.run(dispatcher.handle(command))
    event, _ = _published(producer)
    assert event.payload["ok"] is True
    assert len(limiter.calls) == 2


def test_daily_limit_counting_semantics():
    limiter = RecordingRateLimiter(allowed=True)
    dispatcher, producer, _ = _environment(rate_limiter=limiter)
    draft_id = _create_draft(dispatcher, producer)

    assert limiter.calls == []

    for parameter, value in [("name", "Aria"), ("kind", "Elf")]:
        command = _command(
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "value": value},
        )
        asyncio.run(dispatcher.handle(command))
    assert limiter.calls == []

    command = _command(
        MessageType.CHARACTER_UPDATE_PARAMETER,
        {"draft_id": draft_id, "parameter": "kind", "generate": True},
    )
    asyncio.run(dispatcher.handle(command))
    assert limiter.calls == []

    command = _command(
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "method": "standard"},
    )
    asyncio.run(dispatcher.handle(command))
    assert limiter.calls == []

    command = _command(
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "values": STANDARD_VALUES},
    )
    asyncio.run(dispatcher.handle(command))
    assert limiter.calls == []

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id, "method": "standard"},
    )
    asyncio.run(dispatcher.handle(command))
    assert len(limiter.calls) == 1


def test_character_generate_other_user_draft_rejected():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id, "method": "standard"},
        headers=_headers("user-2"),
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert "not found" in event.payload["error"]


def test_character_generate_invalid_payload_rejected():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload == {
        "ok": False,
        "error": "Invalid character generation request.",
    }


def test_character_generate_unsupported_method_rejected():
    dispatcher, producer, draft_repo = _environment()
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id, "method": "manual"},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert "Unsupported generation method: manual." in event.payload["error"]
    assert draft_repo.rows[0].data == {}


def test_character_generate_missing_draft_id_rejected():
    dispatcher, producer, _ = _environment()
    command = _command(
        MessageType.CHARACTER_GENERATE, {"method": "standard"}
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload == {
        "ok": False,
        "error": "Invalid character generation request.",
    }


def test_character_generate_persistence_failure_returns_error():
    dispatcher, producer, _ = _environment(uow=FlakyUnitOfWork(fail_after=1))
    draft_id = _create_draft(dispatcher, producer)

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id, "method": "standard"},
    )
    asyncio.run(dispatcher.handle(command))

    event, _ = _published(producer)
    assert event.payload["ok"] is False
    assert "could not be completed" in event.payload["error"]


def test_character_generate_publish_failure_propagates():
    dispatcher, producer, _ = _environment()
    draft_id = _create_draft(dispatcher, producer)
    producer.publish.side_effect = RuntimeError("rabbitmq is down")

    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": draft_id, "method": "standard"},
    )
    with pytest.raises(RuntimeError):
        asyncio.run(dispatcher.handle(command))


def test_character_generate_requires_identity_headers():
    dispatcher, producer, draft_repo = _environment()
    command = _command(
        MessageType.CHARACTER_GENERATE,
        {"draft_id": "00000000-0000-0000-0000-000000000000", "method": "standard"},
        headers={},
    )
    with pytest.raises(MessageAuthenticationError):
        asyncio.run(dispatcher.handle(command))
    assert draft_repo.rows == []
    producer.publish.assert_not_awaited()

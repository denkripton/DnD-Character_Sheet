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
from src.modules.character.backstory.dependencies import (
    character_backstory_service_scope,
)
from src.modules.character.backstory.service import BackstoryService
from src.modules.character.base.enums.generation_limits import GenerationLimits
from src.modules.character.draft import CharacterDraftService
from src.modules.character.models import (
    Backstory,
    Character,
    CharacterDraft,
    Combat,
    Feature,
    Personality,
    Proficiency,
    SavingThrows,
    Skill,
    Stat,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.commands.dispatcher_factory import (
    AI_RATE_LIMIT_ERROR_TEXT,
    AI_TIMEOUT_ERROR_TEXT,
    AI_UNAVAILABLE_ERROR_TEXT,
    build_bot_command_dispatcher,
)
from src.utils.exceptions import (
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    MessageAuthenticationError,
)
from src.utils.interfaces.rate_limiter import RateLimitResult
from tests.utils import FakeRepo, FakeUnitOfWork, StubRateLimiter


class DummyUser:
    def __init__(self, id):
        self.id = id


class FakeAI:
    def __init__(self, text="A wandering hero seeks an ancient artifact.", error=None):
        self.text = text
        self.error = error
        self.calls = []

    async def generate(self, prompt, model=None, provider=None):
        self.calls.append({"prompt": prompt, "model": model, "provider": provider})
        if self.error is not None:
            raise self.error
        return self.text


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
            raise OperationalError("INSERT", {}, Exception("database is down"))
        await super().commit()


def _environment(
    ai: FakeAI | None = None,
    draft_rate_limiter=None,
    backstory_rate_limiter=None,
    draft_uow=None,
    backstory_uow=None,
):
    user_repo = FakeRepo(model=DummyUser)
    user_repo.rows.append(DummyUser("user-1"))
    user_repo.rows.append(DummyUser("user-2"))
    draft_repo = FakeRepo(model=CharacterDraft)
    character_repo = FakeRepo(model=Character)
    stats_repo = FakeRepo(model=Stat)
    backstory_repo = FakeRepo(model=Backstory)
    ai = ai or FakeAI()

    draft_service = CharacterDraftService(
        draft_repository=draft_repo,
        character_repository=character_repo,
        stats_repository=stats_repo,
        user_repository=user_repo,
        unit_of_work=draft_uow or FakeUnitOfWork(),
        rate_limiter=draft_rate_limiter or StubRateLimiter(allowed=True),
    )
    guard = CharacterOwnershipGuard(
        character_repository=character_repo, user_repository=user_repo
    )
    backstory_service = BackstoryService(
        ownership_guard=guard,
        backstory_repository=backstory_repo,
        ai_client=ai,
        stats_repository=stats_repo,
        combat_repository=FakeRepo(model=Combat),
        personality_repository=FakeRepo(model=Personality),
        feature_repository=FakeRepo(model=Feature),
        skill_repository=FakeRepo(model=Skill),
        proficiency_repository=FakeRepo(model=Proficiency),
        saving_throws_repository=FakeRepo(model=SavingThrows),
        unit_of_work=backstory_uow or FakeUnitOfWork(),
        rate_limiter=backstory_rate_limiter or StubRateLimiter(allowed=True),
    )

    @asynccontextmanager
    async def draft_scope():
        yield draft_service

    @asynccontextmanager
    async def backstory_scope():
        yield backstory_service

    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(
        producer,
        draft_service_scope=draft_scope,
        backstory_service_scope=backstory_scope,
    )
    return SimpleEnvironment(
        dispatcher=dispatcher,
        producer=producer,
        draft_repo=draft_repo,
        character_repo=character_repo,
        stats_repo=stats_repo,
        backstory_repo=backstory_repo,
        ai=ai,
    )


class SimpleEnvironment:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


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


def _dispatch(env, message_type, payload=None, headers=None):
    asyncio.run(
        env.dispatcher.handle(_command(message_type, payload, headers=headers))
    )
    event, routing_key = env.producer.publish.await_args.args
    return event, routing_key


def _create_draft(env) -> str:
    event, _ = _dispatch(env, MessageType.CHARACTER_CREATE)
    return event.payload["draft"]["id"]


def _create_character(env) -> str:
    draft_id = _create_draft(env)
    for parameter, value in [
        ("name", "Aria"),
        ("kind", "Elf"),
        ("spec_class", "Wizard"),
    ]:
        event, _ = _dispatch(
            env,
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "value": value},
        )
        assert event.payload["ok"] is True
    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_STATS,
        {"draft_id": draft_id, "method": "standard"},
    )
    assert event.payload["ok"] is True
    event, _ = _dispatch(env, MessageType.CHARACTER_SAVE, {"draft_id": draft_id})
    assert event.payload["ok"] is True
    return event.payload["character_id"]


STANDARD_VALUES = ["15", "14", "13", "12", "10", "8"]


def test_character_save_command_creates_character_and_stats():
    env = _environment()
    draft_id = _create_draft(env)
    for parameter, value in [
        ("name", "Aria"),
        ("kind", "Elf"),
        ("spec_class", "Wizard"),
    ]:
        _dispatch(
            env,
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "value": value},
        )
    _dispatch(
        env, MessageType.CHARACTER_STATS, {"draft_id": draft_id, "method": "standard"}
    )

    correlation_id = uuid4()
    asyncio.run(
        env.dispatcher.handle(
            _command(
                MessageType.CHARACTER_SAVE,
                {"draft_id": draft_id},
                correlation_id=correlation_id,
            )
        )
    )
    event, routing_key = env.producer.publish.await_args.args

    assert event.type == MessageType.CHARACTER_SAVED.value
    assert routing_key == "events.character.saved"
    assert event.correlation_id == correlation_id
    assert event.payload["ok"] is True
    assert event.payload["character"]["name"] == "Aria"
    assert event.payload["character"]["kind"] == "Elf"
    assert event.payload["character"]["spec_class"] == "Wizard"
    assert len(env.character_repo.rows) == 1
    assert env.character_repo.rows[0].owner_id == "user-1"
    assert len(env.stats_repo.rows) == 1
    assert env.stats_repo.rows[0].strength == 15
    assert env.stats_repo.rows[0].charisma == 8
    assert env.draft_repo.rows == []


def test_character_save_requires_identity_headers():
    env = _environment()
    draft_id = _create_draft(env)
    published = env.producer.publish.await_count

    with pytest.raises(MessageAuthenticationError):
        asyncio.run(
            env.dispatcher.handle(
                _command(
                    MessageType.CHARACTER_SAVE, {"draft_id": draft_id}, headers={}
                )
            )
        )
    assert env.character_repo.rows == []
    assert env.producer.publish.await_count == published


def test_character_save_other_user_draft_rejected():
    env = _environment()
    draft_id = _create_draft(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_SAVE,
        {"draft_id": draft_id},
        headers=_headers("user-2"),
    )

    assert event.payload["ok"] is False
    assert "not found" in event.payload["error"]
    assert env.character_repo.rows == []


def test_character_save_missing_draft_id_rejected():
    env = _environment()

    event, _ = _dispatch(env, MessageType.CHARACTER_SAVE)

    assert event.payload == {
        "ok": False,
        "error": "Invalid character save request.",
    }


def test_character_save_incomplete_draft_rejected():
    env = _environment()
    draft_id = _create_draft(env)
    _dispatch(
        env,
        MessageType.CHARACTER_UPDATE_PARAMETER,
        {"draft_id": draft_id, "parameter": "name", "value": "Aria"},
    )

    event, _ = _dispatch(env, MessageType.CHARACTER_SAVE, {"draft_id": draft_id})

    assert event.payload["ok"] is False
    assert "required" in event.payload["error"]
    assert env.character_repo.rows == []
    assert len(env.draft_repo.rows) == 1


def test_character_save_invalid_stats_rejected():
    env = _environment()
    draft_id = _create_draft(env)
    for parameter, value in [
        ("name", "Aria"),
        ("kind", "Elf"),
        ("spec_class", "Wizard"),
    ]:
        _dispatch(
            env,
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "value": value},
        )
    env.draft_repo.rows[0].data["stats"] = {
        "strength": 99,
        "dexterity": 12,
        "constitution": 11,
        "intelligence": 10,
        "wisdom": 9,
        "charisma": 8,
    }

    event, _ = _dispatch(env, MessageType.CHARACTER_SAVE, {"draft_id": draft_id})

    assert event.payload["ok"] is False
    assert "3 and 20" in event.payload["error"]
    assert env.character_repo.rows == []
    assert len(env.draft_repo.rows) == 1


def test_character_save_counts_toward_daily_limit():
    limiter = RecordingRateLimiter(allowed=True)
    env = _environment(draft_rate_limiter=limiter)
    draft_id = _create_draft(env)

    for parameter, value in [
        ("name", "Aria"),
        ("kind", "Elf"),
        ("spec_class", "Wizard"),
    ]:
        _dispatch(
            env,
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "value": value},
        )
    _dispatch(
        env, MessageType.CHARACTER_STATS, {"draft_id": draft_id, "values": STANDARD_VALUES}
    )
    assert limiter.calls == []

    event, _ = _dispatch(env, MessageType.CHARACTER_SAVE, {"draft_id": draft_id})

    assert event.payload["ok"] is True
    assert len(limiter.calls) == 1
    assert limiter.calls[0] == (
        "user-1",
        GenerationLimits.KEY_PREFIX.value,
        settings.CHARACTER_GENERATION_DAILY_LIMIT,
        GenerationLimits.DAILY_WINDOW_SECONDS.value,
    )


def test_character_save_rate_limited():
    limiter = RecordingRateLimiter(allowed=False)
    env = _environment(draft_rate_limiter=limiter)
    draft_id = _create_draft(env)

    event, _ = _dispatch(env, MessageType.CHARACTER_SAVE, {"draft_id": draft_id})

    assert event.payload["ok"] is False
    assert "Daily limit reached" in event.payload["error"]
    assert env.character_repo.rows == []


def test_character_save_persistence_failure_returns_error():
    env = _environment(draft_uow=FlakyUnitOfWork(fail_after=5))
    draft_id = _create_draft(env)
    for parameter, value in [
        ("name", "Aria"),
        ("kind", "Elf"),
        ("spec_class", "Wizard"),
    ]:
        _dispatch(
            env,
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "value": value},
        )
    _dispatch(
        env, MessageType.CHARACTER_STATS, {"draft_id": draft_id, "method": "standard"}
    )

    event, _ = _dispatch(env, MessageType.CHARACTER_SAVE, {"draft_id": draft_id})

    assert event.payload["ok"] is False
    assert "could not be completed" in event.payload["error"]


def test_backstory_generate_returns_preview_without_persisting():
    env = _environment()
    character_id = _create_character(env)

    event, routing_key = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id},
    )

    assert event.type == MessageType.CHARACTER_BACKSTORY_GENERATED.value
    assert routing_key == "events.character.backstory_generated"
    assert event.payload == {
        "ok": True,
        "backstory": "A wandering hero seeks an ancient artifact.",
    }
    assert env.backstory_repo.rows == []
    assert len(env.ai.calls) == 1
    prompt = env.ai.calls[0]["prompt"]
    assert "Name: Aria" in prompt
    assert "Race: Elf" in prompt
    assert "Class: Wizard" in prompt


def test_backstory_generate_requires_identity_headers():
    env = _environment()
    character_id = _create_character(env)
    published = env.producer.publish.await_count

    with pytest.raises(MessageAuthenticationError):
        asyncio.run(
            env.dispatcher.handle(
                _command(
                    MessageType.CHARACTER_GENERATE_BACKSTORY,
                    {"character_id": character_id},
                    headers={},
                )
            )
        )
    assert env.producer.publish.await_count == published
    assert env.ai.calls == []


def test_backstory_generate_other_user_character_rejected():
    env = _environment()
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id},
        headers=_headers("user-2"),
    )

    assert event.payload["ok"] is False
    assert "does not exist" in event.payload["error"]
    assert env.ai.calls == []


def test_backstory_generate_missing_character_id_rejected():
    env = _environment()

    event, _ = _dispatch(env, MessageType.CHARACTER_GENERATE_BACKSTORY)

    assert event.payload == {
        "ok": False,
        "error": "Invalid backstory request.",
    }
    assert env.ai.calls == []


def test_backstory_generate_rejects_prompt_too_long():
    env = _environment()
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id, "prompt": "x" * 1001},
    )

    assert event.payload["ok"] is False
    assert event.payload["error"] == "Invalid backstory request."
    assert env.ai.calls == []


def test_backstory_generate_appends_player_prompt():
    env = _environment()
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id, "prompt": "sworn enemy of necromancers"},
    )

    assert event.payload["ok"] is True
    prompt = env.ai.calls[0]["prompt"]
    assert "Additional instructions from the player:" in prompt
    assert "sworn enemy of necromancers" in prompt


def test_backstory_generate_forwards_model_and_provider():
    env = _environment()
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {
            "character_id": character_id,
            "model": "gemini-2.5-pro",
            "provider": "gemini",
        },
    )

    assert event.payload["ok"] is True
    assert env.ai.calls[0]["model"] == "gemini-2.5-pro"
    assert env.ai.calls[0]["provider"] == "gemini"


def test_backstory_generate_user_rate_limited():
    limiter = RecordingRateLimiter(allowed=False)
    env = _environment(backstory_rate_limiter=limiter)
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id},
    )

    assert event.payload["ok"] is False
    assert "Daily limit reached" in event.payload["error"]
    assert len(limiter.calls) == 1
    assert limiter.calls[0] == (
        "user-1",
        GenerationLimits.KEY_PREFIX.value,
        settings.CHARACTER_GENERATION_DAILY_LIMIT,
        GenerationLimits.DAILY_WINDOW_SECONDS.value,
    )
    assert env.ai.calls == []


def test_backstory_generate_ai_timeout_returns_error():
    env = _environment(
        ai=FakeAI(error=AIProviderTimeoutError("timed out", provider="gemini"))
    )
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id},
    )

    assert event.payload == {"ok": False, "error": AI_TIMEOUT_ERROR_TEXT}


def test_backstory_generate_ai_rate_limit_returns_error():
    env = _environment(
        ai=FakeAI(error=AIProviderRateLimitError("quota exceeded", provider="gemini"))
    )
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id},
    )

    assert event.payload == {"ok": False, "error": AI_RATE_LIMIT_ERROR_TEXT}


def test_backstory_generate_ai_provider_error_returns_error():
    env = _environment(
        ai=FakeAI(error=AIProviderError("boom", provider="gemini"))
    )
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id},
    )

    assert event.payload == {"ok": False, "error": AI_UNAVAILABLE_ERROR_TEXT}


def test_backstory_generate_empty_ai_response_returns_error():
    env = _environment(ai=FakeAI(text=""))
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id},
    )

    assert event.payload == {"ok": False, "error": "Empty back story"}


def test_backstory_generate_too_big_ai_response_returns_error():
    env = _environment(ai=FakeAI(text="x" * 1000))
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_GENERATE_BACKSTORY,
        {"character_id": character_id},
    )

    assert event.payload == {"ok": False, "error": "Back story is too big"}


def test_save_backstory_command_persists_text():
    env = _environment()
    character_id = _create_character(env)
    correlation_id = uuid4()

    asyncio.run(
        env.dispatcher.handle(
            _command(
                MessageType.CHARACTER_SAVE_BACKSTORY,
                {"character_id": character_id, "backstory": "Raised by wolves."},
                correlation_id=correlation_id,
            )
        )
    )
    event, routing_key = env.producer.publish.await_args.args

    assert event.type == MessageType.CHARACTER_BACKSTORY_SAVED.value
    assert routing_key == "events.character.backstory_saved"
    assert event.correlation_id == correlation_id
    assert event.payload == {"ok": True, "backstory": "Raised by wolves."}
    assert len(env.backstory_repo.rows) == 1
    assert env.backstory_repo.rows[0].backstory == "Raised by wolves."


def test_save_backstory_upserts_existing_text():
    env = _environment()
    character_id = _create_character(env)

    _dispatch(
        env,
        MessageType.CHARACTER_SAVE_BACKSTORY,
        {"character_id": character_id, "backstory": "First version."},
    )
    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_SAVE_BACKSTORY,
        {"character_id": character_id, "backstory": "Second version."},
    )

    assert event.payload["backstory"] == "Second version."
    assert len(env.backstory_repo.rows) == 1
    assert env.backstory_repo.rows[0].backstory == "Second version."


def test_save_backstory_requires_identity_headers():
    env = _environment()
    character_id = _create_character(env)
    published = env.producer.publish.await_count

    with pytest.raises(MessageAuthenticationError):
        asyncio.run(
            env.dispatcher.handle(
                _command(
                    MessageType.CHARACTER_SAVE_BACKSTORY,
                    {"character_id": character_id, "backstory": "Text."},
                    headers={},
                )
            )
        )
    assert env.producer.publish.await_count == published
    assert env.backstory_repo.rows == []


def test_save_backstory_other_user_character_rejected():
    env = _environment()
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_SAVE_BACKSTORY,
        {"character_id": character_id, "backstory": "Intruder text."},
        headers=_headers("user-2"),
    )

    assert event.payload["ok"] is False
    assert "does not exist" in event.payload["error"]
    assert env.backstory_repo.rows == []


def test_save_backstory_missing_text_rejected():
    env = _environment()
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_SAVE_BACKSTORY,
        {"character_id": character_id},
    )

    assert event.payload == {
        "ok": False,
        "error": "Backstory text is required.",
    }


def test_save_backstory_blank_text_rejected():
    env = _environment()
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_SAVE_BACKSTORY,
        {"character_id": character_id, "backstory": "   "},
    )

    assert event.payload == {
        "ok": False,
        "error": "Backstory text is required.",
    }
    assert env.backstory_repo.rows == []


def test_save_backstory_too_long_text_rejected():
    env = _environment()
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_SAVE_BACKSTORY,
        {"character_id": character_id, "backstory": "x" * 10001},
    )

    assert event.payload["ok"] is False
    assert "10000" in event.payload["error"]
    assert env.backstory_repo.rows == []


def test_save_backstory_persistence_failure_returns_error():
    env = _environment(backstory_uow=FlakyUnitOfWork(fail_after=0))
    character_id = _create_character(env)

    event, _ = _dispatch(
        env,
        MessageType.CHARACTER_SAVE_BACKSTORY,
        {"character_id": character_id, "backstory": "Raised by wolves."},
    )

    assert event.payload["ok"] is False
    assert "could not be completed" in event.payload["error"]


def test_backstory_scope_is_importable():
    assert character_backstory_service_scope is not None

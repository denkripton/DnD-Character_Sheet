import asyncio

import pytest

from src.config import settings
from src.utils.exceptions import RateLimitExceeded
from src.modules.character.base.enums.generation_limits import GenerationLimits
from src.modules.character.base.schemas import CharacterCreateSchema
from src.modules.character.base.service import CharacterService
from src.modules.character.models import Character
from src.utils.exception_handlers import rate_limit_exceeded_handler
from src.utils.interfaces.rate_limiter import RateLimitResult
from tests.utils import FakeRepo, FakeUnitOfWork, build_guard


class StubRateLimiter:
    def __init__(self, result: RateLimitResult):
        self.result = result
        self.calls = []

    async def is_limited(self, user_id, category, max_requests, time_window):
        self.calls.append((user_id, category, max_requests, time_window))
        return self.result


class StubCache:
    async def get(self, key):
        return None

    async def set(self, key, value):
        return True

    async def delete_pattern(self, pattern):
        return None


def build_service(result: RateLimitResult):
    stub_limiter = StubRateLimiter(result)
    user_repo = FakeRepo(None)
    user_repo.rows.append(type("User", (), {"id": "user-42"})())
    character_repo = FakeRepo(Character)
    service = CharacterService(
        character_repository=character_repo,
        user_repository=user_repo,
        ownership_guard=build_guard(character_repo, user_repo, "user-42"),
        combat_repository=FakeRepo(None),
        stats_repository=FakeRepo(None),
        unit_of_work=FakeUnitOfWork(),
        rate_limiter=stub_limiter,
    )
    return service, stub_limiter, character_repo


def test_character_creation_allowed_within_limit_and_records_usage(monkeypatch):
    monkeypatch.setattr(
        "src.modules.character.base.service.cache", StubCache()
    )
    service, stub_limiter, character_repo = build_service(
        RateLimitResult(
            allowed=True,
            current_usage=1,
            max_allowed=5,
            remaining=4,
            retry_after=0,
        )
    )
    data = CharacterCreateSchema(
        name="Grog", spec_class="Barbarian", kind="Human"
    )

    async def flow():
        created = await service.character_creation(user_id="user-42", data=data)
        assert created.id is not None
        assert len(character_repo.rows) == 1
        assert stub_limiter.calls == [
            (
                "user-42",
                GenerationLimits.KEY_PREFIX.value,
                settings.CHARACTER_GENERATION_DAILY_LIMIT,
                GenerationLimits.DAILY_WINDOW_SECONDS.value,
            )
        ]

    asyncio.run(flow())


def test_character_creation_raises_when_daily_limit_exceeded(monkeypatch):
    monkeypatch.setattr(
        "src.modules.character.base.service.cache", StubCache()
    )
    service, stub_limiter, character_repo = build_service(
        RateLimitResult(
            allowed=False,
            current_usage=5,
            max_allowed=5,
            remaining=0,
            retry_after=3600,
        )
    )
    data = CharacterCreateSchema(
        name="Grog", spec_class="Barbarian", kind="Human"
    )

    async def flow():
        with pytest.raises(RateLimitExceeded) as exc_info:
            await service.character_creation(user_id="user-42", data=data)
        exc = exc_info.value
        assert exc.status_code == 429
        assert exc.used == 5
        assert exc.limit == 5
        assert exc.retry_after == 3600
        assert len(character_repo.rows) == 0
        assert len(stub_limiter.calls) == 1

    asyncio.run(flow())


def test_generate_character_enforces_same_daily_limit(monkeypatch):
    monkeypatch.setattr(
        "src.modules.character.base.service.cache", StubCache()
    )
    service, stub_limiter, character_repo = build_service(
        RateLimitResult(
            allowed=False,
            current_usage=5,
            max_allowed=5,
            remaining=0,
            retry_after=3600,
        )
    )

    async def flow():
        with pytest.raises(RateLimitExceeded):
            await service.generate_character(user_id="user-42")
        assert len(character_repo.rows) == 0
        assert stub_limiter.calls == [
            (
                "user-42",
                GenerationLimits.KEY_PREFIX.value,
                settings.CHARACTER_GENERATION_DAILY_LIMIT,
                GenerationLimits.DAILY_WINDOW_SECONDS.value,
            )
        ]

    asyncio.run(flow())


def test_rate_limit_exceeded_handler_returns_429_with_metadata():
    exc = RateLimitExceeded(limit=5, used=5, retry_after=7200)
    response = asyncio.run(rate_limit_exceeded_handler(request=None, exc=exc))

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "7200"
    detail = response.body.decode()
    assert '"current_usage":5' in detail
    assert '"max_allowed":5' in detail
    assert '"remaining":0' in detail
    assert '"retry_after":7200' in detail
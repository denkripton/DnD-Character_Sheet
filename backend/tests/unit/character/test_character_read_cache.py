import asyncio
import uuid

import pytest
from src.config import settings
from src.infrastructure.redis.cache import RedisCache
from src.modules.character.base.schemas import CharacterUpdateSchema
from src.modules.character.base.service import CharacterService
from src.modules.character.models import Character, Combat, Stat
from src.utils.exceptions import ServiceError
from tests.utils import (
    FakeRedis,
    FakeRepo,
    FakeUnitOfWork,
    StubRateLimiter,
    build_guard,
    build_owned_character,
)

USER_ID = "user-1"
OTHER_USER_ID = "user-2"
CHAR_ID = uuid.uuid4()


class DummyUser:
    def __init__(self, id):
        self.id = id


class CountingRepo(FakeRepo):
    def __init__(self, model):
        super().__init__(model)
        self.reads = 0

    async def get_one(self, **kwargs):
        self.reads += 1
        return await super().get_one(**kwargs)

    async def get_many(self, skip=0, limit=None, **kwargs):
        self.reads += 1
        return await super().get_many(skip=skip, limit=limit, **kwargs)


def _service(monkeypatch, fake_redis=None):
    character_repo = CountingRepo(model=Character)
    user_repo = FakeRepo(model=DummyUser)
    guard = build_guard(character_repo, user_repo, USER_ID)
    user_repo.rows.append(DummyUser(OTHER_USER_ID))
    combat_repo = FakeRepo(model=Combat)
    stats_repo = FakeRepo(model=Stat)
    fake = fake_redis if fake_redis is not None else FakeRedis()
    cache = RedisCache(fake)
    monkeypatch.setattr("src.modules.character.base.service.cache", cache)
    service = CharacterService(
        character_repository=character_repo,
        user_repository=user_repo,
        ownership_guard=guard,
        combat_repository=combat_repo,
        stats_repository=stats_repo,
        unit_of_work=FakeUnitOfWork(),
        rate_limiter=StubRateLimiter(),
    )
    return service, character_repo, fake, cache


def test_character_by_id_cache_miss_reads_db_and_populates(monkeypatch):
    service, repo, fake, cache = _service(monkeypatch)
    build_owned_character(repo, CHAR_ID, USER_ID)

    async def flow():
        result = await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert result.id == CHAR_ID
        assert repo.reads == 1

        key = f"characters:by_id:{USER_ID}:{CHAR_ID}"
        assert key in fake.store
        cached = await cache.get(key)
        assert cached["name"] == "Grog"

    asyncio.run(flow())


def test_character_by_id_cache_hit_skips_db(monkeypatch):
    service, repo, _, _ = _service(monkeypatch)
    build_owned_character(repo, CHAR_ID, USER_ID)

    async def flow():
        first = await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert repo.reads == 1

        second = await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert repo.reads == 1
        assert first == second

    asyncio.run(flow())


def test_character_list_cache_miss_population_and_hit(monkeypatch):
    service, repo, fake, cache = _service(monkeypatch)
    build_owned_character(repo, CHAR_ID, USER_ID)

    async def flow():
        first = await service.get_all_characters(USER_ID)
        assert repo.reads == 1
        assert len(first) == 1

        key = f"characters:list:{USER_ID}"
        assert key in fake.store
        assert (await cache.get(key))[0]["name"] == "Grog"

        second = await service.get_all_characters(USER_ID)
        assert repo.reads == 1
        assert [c.id for c in second] == [CHAR_ID]

    asyncio.run(flow())


def test_update_character_invalidates_cached_reads(monkeypatch):
    service, repo, fake, _ = _service(monkeypatch)
    build_owned_character(repo, CHAR_ID, USER_ID)

    async def flow():
        await service.get_character_by_id(USER_ID, str(CHAR_ID))
        await service.get_all_characters(USER_ID)

        updated = await service.update_character(
            USER_ID, CHAR_ID, CharacterUpdateSchema(name="Renamed")
        )
        assert updated.name == "Renamed"

        by_id_key = f"characters:by_id:{USER_ID}:{CHAR_ID}"
        list_key = f"characters:list:{USER_ID}"
        assert by_id_key not in fake.store
        assert list_key not in fake.store

        fetched = await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert fetched.name == "Renamed"
        assert by_id_key in fake.store

        listed = await service.get_all_characters(USER_ID)
        assert listed[0].name == "Renamed"

    asyncio.run(flow())


def test_delete_character_invalidates_cached_reads(monkeypatch):
    service, repo, fake, _ = _service(monkeypatch)
    build_owned_character(repo, CHAR_ID, USER_ID)

    async def flow():
        await service.get_character_by_id(USER_ID, str(CHAR_ID))
        await service.get_all_characters(USER_ID)
        assert fake.store

        result = await service.delete_character(USER_ID, CHAR_ID)
        assert result == {"message": "Character has been deleted"}
        assert fake.store == {}

        with pytest.raises(ServiceError) as exc_info:
            await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_cached_character_expires_and_refetches_from_db(monkeypatch):
    service, repo, fake, _ = _service(monkeypatch)
    build_owned_character(repo, CHAR_ID, USER_ID)

    async def flow():
        await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert repo.reads == 1

        fake.advance(settings.CACHE_TTL + 1)

        result = await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert result.id == CHAR_ID
        assert repo.reads == 2

    asyncio.run(flow())


def test_redis_failure_falls_back_to_postgres(monkeypatch):
    service, repo, _, _ = _service(monkeypatch, FakeRedis(fail=True))
    build_owned_character(repo, CHAR_ID, USER_ID)

    async def flow():
        first = await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert first.id == CHAR_ID
        assert repo.reads == 1

        second = await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert second.id == CHAR_ID
        assert repo.reads == 2

        listed = await service.get_all_characters(USER_ID)
        assert len(listed) == 1

        updated = await service.update_character(
            USER_ID, CHAR_ID, CharacterUpdateSchema(name="Renamed")
        )
        assert updated.name == "Renamed"

        deleted = await service.delete_character(USER_ID, CHAR_ID)
        assert deleted == {"message": "Character has been deleted"}

    asyncio.run(flow())


def test_cached_character_not_served_to_non_owner(monkeypatch):
    service, repo, fake, _ = _service(monkeypatch)
    build_owned_character(repo, CHAR_ID, USER_ID)

    async def flow():
        await service.get_character_by_id(USER_ID, str(CHAR_ID))
        owner_key = f"characters:by_id:{USER_ID}:{CHAR_ID}"
        assert owner_key in fake.store

        with pytest.raises(ServiceError) as exc_info:
            await service.get_character_by_id(OTHER_USER_ID, str(CHAR_ID))
        assert exc_info.value.status_code == 422
        assert f"characters:by_id:{OTHER_USER_ID}:{CHAR_ID}" not in fake.store

        served = await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert served.id == CHAR_ID

    asyncio.run(flow())


def test_stale_cache_entry_not_used_after_ownership_denied(monkeypatch):
    service, repo, fake, _ = _service(monkeypatch)
    build_owned_character(repo, CHAR_ID, USER_ID)

    async def flow():
        with pytest.raises(ServiceError):
            await service.get_character_by_id(OTHER_USER_ID, str(CHAR_ID))
        assert fake.store == {}

        await service.get_character_by_id(USER_ID, str(CHAR_ID))
        assert f"characters:by_id:{USER_ID}:{CHAR_ID}" in fake.store

        with pytest.raises(ServiceError):
            await service.get_character_by_id(OTHER_USER_ID, str(CHAR_ID))
        assert f"characters:by_id:{OTHER_USER_ID}:{CHAR_ID}" not in fake.store

    asyncio.run(flow())

import asyncio

from pydantic import BaseModel

from src.infrastructure.redis.cache import RedisCache
from tests.utils import FakeRedis


class SampleModel(BaseModel):
    name: str
    level: int


def test_cache_get_set_roundtrip_and_ttl():
    fake = FakeRedis()
    cache = RedisCache(fake, default_ttl=300)

    async def flow():
        await cache.set("character:1", {"name": "Grog", "level": 3})
        assert await cache.get("character:1") == {"name": "Grog", "level": 3}
        assert fake.expirations["character:1"] == 300

        await cache.set("character:2", {"name": "Ela"}, ttl=60)
        assert fake.expirations["character:2"] == 60

    asyncio.run(flow())


def test_cache_serializes_pydantic_models():
    fake = FakeRedis()
    cache = RedisCache(fake)

    async def flow():
        await cache.set("model:1", SampleModel(name="Grog", level=5))
        assert await cache.get("model:1") == {"name": "Grog", "level": 5}

    asyncio.run(flow())


def test_cache_get_missing_and_invalid_json_returns_none():
    fake = FakeRedis()
    cache = RedisCache(fake)

    async def flow():
        assert await cache.get("missing") is None
        fake.store["broken"] = b"not-json"
        assert await cache.get("broken") is None

    asyncio.run(flow())


def test_cache_delete_exists_and_scan():
    fake = FakeRedis()
    cache = RedisCache(fake)

    async def flow():
        await cache.set("character:list:user-1", [1])
        await cache.set("character:list:user-2", [2])
        assert await cache.exists("character:list:user-1") is True

        keys = [key async for key in cache.scan("character:list:*")]
        assert sorted(keys) == ["character:list:user-1", "character:list:user-2"]

        await cache.delete_pattern("character:list:*")
        assert await cache.exists("character:list:user-1") is False
        assert fake.store == {}

        await cache.set("single", 1)
        await cache.delete("single")
        assert await cache.get("single") is None

    asyncio.run(flow())


def test_cache_fails_open_on_read_write_when_redis_is_down():
    fake = FakeRedis(fail=True)
    cache = RedisCache(fake)

    async def flow():
        assert await cache.get("any") is None
        await cache.set("any", {"a": 1})
        await cache.delete("any")
        await cache.delete_pattern("any*")

    asyncio.run(flow())


if __name__ == "__main__":
    test_cache_get_set_roundtrip_and_ttl()
    test_cache_serializes_pydantic_models()
    test_cache_get_missing_and_invalid_json_returns_none()
    test_cache_delete_exists_and_scan()
    test_cache_fails_open_on_read_write_when_redis_is_down()
    print("redis cache tests passed")

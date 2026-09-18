import asyncio

from src.infrastructure.redis.rate_limiter import RedisRateLimiter
from tests.utils import FakeRedis


def test_rate_limiter_allows_until_limit_then_blocks():
    fake = FakeRedis()
    limiter = RedisRateLimiter(fake)

    async def flow():
        first = await limiter.hit("user-1", limit=2, window_seconds=60)
        assert first.allowed is True
        assert first.remaining == 1
        assert first.retry_after == 0

        second = await limiter.hit("user-1", limit=2, window_seconds=60)
        assert second.allowed is True
        assert second.remaining == 0

        third = await limiter.hit("user-1", limit=2, window_seconds=60)
        assert third.allowed is False
        assert third.remaining == 0
        assert third.retry_after == 60

    asyncio.run(flow())


def test_rate_limiter_sets_expiry_only_on_first_hit():
    fake = FakeRedis()
    limiter = RedisRateLimiter(fake)

    async def flow():
        await limiter.hit("user-1", limit=5, window_seconds=30)
        assert fake.expirations["user-1"] == 30
        await limiter.hit("user-1", limit=5, window_seconds=30)
        assert fake.expirations["user-1"] == 30

    asyncio.run(flow())


def test_rate_limiter_fails_open_when_redis_is_down():
    fake = FakeRedis(fail=True)
    limiter = RedisRateLimiter(fake)

    async def flow():
        result = await limiter.hit("user-1", limit=1, window_seconds=60)
        assert result.allowed is True
        assert result.remaining == 1
        assert result.retry_after == 0

    asyncio.run(flow())


if __name__ == "__main__":
    test_rate_limiter_allows_until_limit_then_blocks()
    test_rate_limiter_sets_expiry_only_on_first_hit()
    test_rate_limiter_fails_open_when_redis_is_down()
    print("redis rate limiter tests passed")

import asyncio
import time

from src.infrastructure.redis.rate_limiter import RedisRateLimiter
from tests.utils import FakeRedis


class FakeClock:
    def __init__(self, now_ms):
        self.now_ms = now_ms

    def __call__(self):
        return self.now_ms


def test_rate_limiter_blocks_exceeding_limit():
    fake = FakeRedis()
    limiter = RedisRateLimiter(fake)

    async def flow():
        first = await limiter.is_limited(
            user_id="user-1", category="messages", max_requests=2, time_window=60
        )
        assert first.allowed is True
        assert first.current_usage == 0
        assert first.max_allowed == 2
        assert first.remaining == 2
        assert first.retry_after == 0

        second = await limiter.is_limited(
            user_id="user-1", category="messages", max_requests=2, time_window=60
        )
        assert second.allowed is True
        assert second.current_usage == 1
        assert second.remaining == 1

        third = await limiter.is_limited(
            user_id="user-1", category="messages", max_requests=2, time_window=60
        )
        assert third.allowed is False
        assert third.current_usage == 2
        assert third.max_allowed == 2
        assert third.remaining == 0
        assert third.retry_after > 0

    asyncio.run(flow())


def test_rate_limiter_separates_users_and_categories():
    fake = FakeRedis()
    limiter = RedisRateLimiter(fake)

    async def flow():
        for _ in range(2):
            user_a = await limiter.is_limited(
                user_id="a", category="messages", max_requests=2, time_window=60
            )
            assert user_a.allowed is True
            first_b = await limiter.is_limited(
                user_id="b", category="messages", max_requests=2, time_window=60
            )
            assert first_b.allowed is True

        first_a_other = await limiter.is_limited(
            user_id="a", category="other", max_requests=2, time_window=60
        )
        assert first_a_other.allowed is True

        third_user_a = await limiter.is_limited(
            user_id="a", category="messages", max_requests=2, time_window=60
        )
        assert third_user_a.allowed is False

    asyncio.run(flow())


def test_rate_limiter_fails_open_when_redis_is_down():
    fake = FakeRedis(fail=True)
    limiter = RedisRateLimiter(fake)

    async def flow():
        result = await limiter.is_limited(
            user_id="user-1", category="messages", max_requests=1, time_window=60
        )
        assert result.allowed is True
        assert result.current_usage == 0
        assert result.max_allowed == 1
        assert result.remaining == 1
        assert result.retry_after == 0

    asyncio.run(flow())


def test_concurrent_hits_cannot_exceed_limit():
    fake = FakeRedis()
    limiter = RedisRateLimiter(fake)

    async def flow():
        hits = await asyncio.gather(
            *[
                limiter.is_limited(
                    user_id="user-1", category="messages", max_requests=3, time_window=60
                )
                for _ in range(10)
            ]
        )
        allowed = [h for h in hits if h.allowed]
        blocked = [h for h in hits if not h.allowed]
        assert len(allowed) == 3
        assert len(blocked) == 7
        assert all(up.current_usage < 3 for up in allowed)
        assert all(blocked_h.retry_after > 0 for blocked_h in blocked)

    asyncio.run(flow())


def test_rate_limiter_resets_after_window_elapses():
    fake = FakeRedis()
    window = 24 * 60 * 60
    clock = FakeClock(now_ms=time.time() * 1000)
    limiter = RedisRateLimiter(fake, now_ms=clock)

    async def flow():
        for _ in range(5):
            result = await limiter.is_limited(
                user_id="user-1", category="messages", max_requests=5, time_window=window
            )
            assert result.allowed is True

        blocked = await limiter.is_limited(
            user_id="user-1", category="messages", max_requests=5, time_window=window
        )
        assert blocked.allowed is False
        assert blocked.current_usage == 5
        assert blocked.retry_after > 0

        clock.now_ms += window * 1000 + 1
        reset = await limiter.is_limited(
            user_id="user-1", category="messages", max_requests=5, time_window=window
        )
        assert reset.allowed is True
        assert reset.current_usage == 0
        assert reset.remaining == 5
        assert fake.expirations["limiter:messages:user-1"] == window

    asyncio.run(flow())


if __name__ == "__main__":
    test_rate_limiter_blocks_exceeding_limit()
    test_rate_limiter_separates_users_and_categories()
    test_rate_limiter_fails_open_when_redis_is_down()
    test_concurrent_hits_cannot_exceed_limit()
    test_rate_limiter_resets_after_window_elapses()
    print("redis rate limiter tests passed")
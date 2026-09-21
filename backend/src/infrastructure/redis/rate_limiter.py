import logging
import random
import time
from collections.abc import Callable

from redis.asyncio import Redis

from src.utils.interfaces.rate_limiter import RateLimiter, RateLimitResult

logger = logging.getLogger(__name__)


class RedisRateLimiter(RateLimiter):
    def __init__(self, client: Redis, now_ms: Callable[[], float] | None = None):
        self._client = client
        self._now_ms = now_ms or (lambda: time.time() * 1000)

    async def is_limited(
        self, user_id: str, category: str, max_requests: int, time_window: int
    ) -> RateLimitResult:
        try:
            key = f"limiter:{category}:{user_id}"
            current_ms = self._now_ms()
            window_ms = time_window * 1000
            window_start = current_ms - window_ms
            request_token = f"{current_ms}-{random.randint(0, 100_000)}"

            async with self._client.pipeline() as pipe:
                pipe.zremrangebyscore(name=key, min=0, max=window_start)
                pipe.zcard(key)
                pipe.zadd(key, {request_token: current_ms})
                pipe.expire(key, time_window)
                pipe.zrange(key, 0, 0, withscores=True)
                _, current_count, _, _, oldest = await pipe.execute()
        except Exception as exc:
            logger.warning(
                "Redis rate limiting failed for category %s user %s: %s",
                category,
                user_id,
                exc,
            )
            return RateLimitResult(
                allowed=True,
                current_usage=0,
                max_allowed=max_requests,
                remaining=max_requests,
                retry_after=0,
            )

        if current_count >= max_requests:
            oldest_score = oldest[0][1] if oldest else window_start
            retry_after = int((oldest_score + window_ms - current_ms) / 1000) + 1
            return RateLimitResult(
                allowed=False,
                current_usage=current_count,
                max_allowed=max_requests,
                remaining=0,
                retry_after=retry_after,
            )
        return RateLimitResult(
            allowed=True,
            current_usage=current_count,
            max_allowed=max_requests,
            remaining=max_requests - current_count,
            retry_after=0,
        )
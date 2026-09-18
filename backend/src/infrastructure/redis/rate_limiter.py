import logging

from redis.asyncio import Redis

from src.utils.interfaces.rate_limiter import RateLimiter, RateLimitResult

logger = logging.getLogger(__name__)


class RedisRateLimiter(RateLimiter):
    def __init__(self, client: Redis):
        self._client = client

    async def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        try:
            count = await self._client.incr(key)
            if count == 1:
                await self._client.expire(key, window_seconds)
            ttl = await self._client.ttl(key)
        except Exception as exc:
            logger.warning("Redis rate limiting failed for key %s: %s", key, exc)
            return RateLimitResult(allowed=True, remaining=limit, retry_after=0)

        if count > limit:
            retry_after = ttl if isinstance(ttl, int) and ttl > 0 else window_seconds
            return RateLimitResult(allowed=False, remaining=0, retry_after=retry_after)
        return RateLimitResult(allowed=True, remaining=limit - count, retry_after=0)

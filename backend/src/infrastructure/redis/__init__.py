from redis.asyncio import Redis

from src.config import CACHE_TTL, settings
from src.infrastructure.redis.cache import RedisCache
from src.infrastructure.redis.rate_limiter import RedisRateLimiter
from src.repositories.redis import RedisRepository
from src.utils.interfaces.cache import CacheRepository
from src.utils.interfaces.rate_limiter import RateLimiter

redis = Redis.from_url(
    settings.REDIS_URL,
    socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
    decode_responses=False,
)

cache: CacheRepository = RedisCache(
    client=redis,
    default_ttl=CACHE_TTL,
)

rate_limiter: RateLimiter = RedisRateLimiter(redis)

__all__ = [
    "RedisCache",
    "RedisRateLimiter",
    "RedisRepository",
    "cache",
    "rate_limiter",
    "redis",
]
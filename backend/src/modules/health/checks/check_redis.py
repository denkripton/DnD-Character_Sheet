import asyncio

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError
from src.config import settings
from src.modules.health.checks.status import DOWN, UP


async def check_redis(redis_client: Redis) -> str:
    try:
        async with asyncio.timeout(settings.HEALTH_CHECK_TIMEOUT_SECONDS):
            await redis_client.ping()
    except (OSError, RedisError) as exc:
        structlog.get_logger("src.modules.health.service").warning(
            "redis_check_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return DOWN
    return UP

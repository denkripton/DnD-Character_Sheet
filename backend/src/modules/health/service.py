import asyncio

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine
from src.config import settings
from src.infrastructure.rabbitmq.bus import RabbitMQMessageBus
from src.modules.health.schemas import ReadinessResponseSchema
from src.utils.exceptions import RabbitMQConnectionError

UP = "up"
DOWN = "down"


async def check_postgres(engine: AsyncEngine) -> str:
    try:
        async with asyncio.timeout(settings.HEALTH_CHECK_TIMEOUT_SECONDS):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except (OSError, SQLAlchemyError) as exc:
        structlog.get_logger(__name__).warning(
            "postgres_check_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return DOWN
    return UP


async def check_redis(redis_client: Redis) -> str:
    try:
        async with asyncio.timeout(settings.HEALTH_CHECK_TIMEOUT_SECONDS):
            await redis_client.ping()
    except (OSError, RedisError) as exc:
        structlog.get_logger(__name__).warning(
            "redis_check_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return DOWN
    return UP


async def check_rabbitmq(message_bus: RabbitMQMessageBus) -> str:
    try:
        async with asyncio.timeout(settings.HEALTH_CHECK_TIMEOUT_SECONDS):
            healthy = await message_bus.health_check()
    except (OSError, RabbitMQConnectionError) as exc:
        structlog.get_logger(__name__).warning(
            "rabbitmq_check_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return DOWN
    return UP if healthy else DOWN


class HealthService:
    def __init__(
        self,
        engine: AsyncEngine,
        redis_client: Redis,
        message_bus: RabbitMQMessageBus,
    ):
        self._engine = engine
        self._redis_client = redis_client
        self._message_bus = message_bus

    async def readiness(self) -> ReadinessResponseSchema:
        postgres_status, redis_status, rabbitmq_status = await asyncio.gather(
            check_postgres(self._engine),
            check_redis(self._redis_client),
            check_rabbitmq(self._message_bus),
        )
        checks = {
            "postgres": postgres_status,
            "redis": redis_status,
            "rabbitmq": rabbitmq_status,
        }
        status = "ready" if all(value == UP for value in checks.values()) else "not_ready"
        return ReadinessResponseSchema(status=status, checks=checks)

import asyncio

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine
from src.infrastructure.rabbitmq.bus import RabbitMQMessageBus
from src.modules.health.checks.check_postgres import check_postgres
from src.modules.health.checks.check_rabbitmq import check_rabbitmq
from src.modules.health.checks.check_redis import check_redis
from src.modules.health.checks.status import UP
from src.modules.health.schemas import ReadinessResponseSchema


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

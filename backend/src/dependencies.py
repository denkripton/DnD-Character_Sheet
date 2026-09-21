from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.databases.sql import AsyncSessionLocal
from src.infrastructure.rabbitmq.bus import RabbitMQMessageBus
from src.infrastructure.rabbitmq.connection import RabbitMQConnection
from src.infrastructure.rabbitmq.topology import Topology
from src.infrastructure.redis import cache, rate_limiter, redis
from src.messaging.interfaces import MessageBus
from src.utils.interfaces.cache import CacheRepository
from src.utils.interfaces.rate_limiter import RateLimiter
from src.utils.unit_of_work import UnitOfWork


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_unit_of_work(
    session: AsyncSession = Depends(get_session),
) -> UnitOfWork:
    uow = UnitOfWork(session=session)
    try:
        yield uow
    except Exception:
        await uow.rollback()
        raise


class RepoFactory:
    def __init__(self, repo):
        self.repository_class = repo

    def __call__(self, session: AsyncSession = Depends(get_session)):
        return self.repository_class(session)


def get_redis_client() -> Redis:
    return redis


def get_cache() -> CacheRepository:
    return cache


def get_rate_limiter() -> RateLimiter:
    return rate_limiter


def get_message_bus() -> MessageBus:
    return RabbitMQMessageBus(
        connection=RabbitMQConnection(
            url=settings.RABBITMQ_URL,
            reconnect_interval_seconds=settings.RABBITMQ_RECONNECT_INTERVAL_SECONDS,
        ),
        topology=Topology(
            exchange_name=settings.RABBITMQ_EXCHANGE,
            queue_prefix=settings.RABBITMQ_QUEUE_PREFIX,
            exchange_type=settings.RABBITMQ_EXCHANGE_TYPE,
            retry_delay_seconds=settings.RABBITMQ_RETRY_DELAY_SECONDS,
        ),
        prefetch_count=settings.RABBITMQ_PREFETCH_COUNT,
        max_retries=settings.RABBITMQ_MAX_RETRIES,
    )

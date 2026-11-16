from redis.asyncio import Redis

from src.infrastructure.redis import redis


def get_redis_client() -> Redis:
    return redis

import json
from typing import Any

from redis.asyncio import Redis

from src.config import CACHE_TTL, settings
from src.utils.interfaces.cache import CacheRepository


class RedisRepository(CacheRepository):
    def __init__(self, client: Redis | None = None):
        self.client = client or Redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=1
        )

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self.client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = CACHE_TTL) -> None:
        try:
            await self.client.set(key, json.dumps(value), ex=ttl)
        except Exception:
            pass

    async def delete(self, key: str) -> None:
        try:
            await self.client.delete(key)
        except Exception:
            pass

    async def delete_pattern(self, pattern: str) -> None:
        try:
            async for key in self.client.scan_iter(match=pattern):
                await self.client.delete(key)
        except Exception:
            pass

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    async def scan(self, pattern: str):
        async for key in self.client.scan_iter(match=pattern):
            yield key
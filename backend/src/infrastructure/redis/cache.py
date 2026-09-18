import json
from typing import Any, Optional

from pydantic import BaseModel
from redis.asyncio import Redis

from src.config import CACHE_TTL
from src.repositories.redis import RedisRepository


def _serialize(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, default=str)


class RedisCache(RedisRepository):
    def __init__(self, client: Redis | None = None, default_ttl: int = CACHE_TTL):
        super().__init__(client=client)
        self._default_ttl = default_ttl

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            await self.client.set(
                key,
                _serialize(value),
                ex=ttl if ttl is not None else self._default_ttl,
            )
        except Exception:
            pass
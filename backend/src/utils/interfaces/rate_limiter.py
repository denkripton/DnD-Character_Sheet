from abc import ABC, abstractmethod

from src.infrastructure.redis.enums import RateLimitResult


class RateLimiter(ABC):
    @abstractmethod
    async def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        raise NotImplementedError("Method must be redefined")
from abc import ABC, abstractmethod

from src.infrastructure.redis.enums import RateLimitResult


class RateLimiter(ABC):
    @abstractmethod
    async def is_limited(
        self, user_id: str, category: str, max_requests: int, time_window: int
    ) -> RateLimitResult:
        raise NotImplementedError("Method must be redefined")
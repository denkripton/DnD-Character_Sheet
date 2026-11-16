from abc import ABC, abstractmethod

from src.utils.interfaces.rate_limit_result import RateLimitResult


class RateLimiter(ABC):
    @abstractmethod
    async def is_limited(
        self, user_id: str, category: str, max_requests: int, time_window: int
    ) -> RateLimitResult:
        raise NotImplementedError("Method must be redefined")

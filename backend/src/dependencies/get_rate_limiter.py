from src.infrastructure.redis import rate_limiter
from src.utils.interfaces.rate_limiter import RateLimiter


def get_rate_limiter() -> RateLimiter:
    return rate_limiter

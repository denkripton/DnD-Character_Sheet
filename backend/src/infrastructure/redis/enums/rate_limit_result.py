from typing import NamedTuple


class RateLimitResult(NamedTuple):
    allowed: bool
    remaining: int
    retry_after: int
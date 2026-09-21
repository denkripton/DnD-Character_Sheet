from typing import NamedTuple


class RateLimitResult(NamedTuple):
    allowed: bool
    current_usage: int
    max_allowed: int
    remaining: int
    retry_after: int
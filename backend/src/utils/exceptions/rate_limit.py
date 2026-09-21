class RateLimitExceeded(Exception):
    def __init__(self, limit: int, used: int, retry_after: int):
        self.message = f"Daily limit reached: {used}/{limit}"
        self.status_code = 429
        self.limit = limit
        self.used = used
        self.retry_after = retry_after
        super().__init__(self.message)
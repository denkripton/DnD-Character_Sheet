class AIProviderError(Exception):
    def __init__(
        self,
        message: str,
        provider: str | None = None,
        retry_after: int | None = None,
    ):
        self.message = message
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(message)

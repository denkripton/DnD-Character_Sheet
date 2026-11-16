from fastapi import FastAPI

from src.utils.exceptions import (
    AIProviderError,
    RateLimitExceeded,
    ServiceError,
)
from src.utils.exceptions.handlers.ai_provider_error_handler import (
    ai_provider_error_handler,
)
from src.utils.exceptions.handlers.rate_limit_exceeded_handler import (
    rate_limit_exceeded_handler,
)
from src.utils.exceptions.handlers.service_error_handler import (
    service_error_handler,
)
from src.utils.exceptions.handlers.unhandled_exception_handler import (
    unhandled_exception_handler,
)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, service_error_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_exception_handler(AIProviderError, ai_provider_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

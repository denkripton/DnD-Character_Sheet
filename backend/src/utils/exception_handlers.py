from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.utils.exceptions import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    RateLimitExceeded,
    ServiceError,
)


async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": {
                "message": exc.message,
                "current_usage": exc.used,
                "max_allowed": exc.limit,
                "remaining": 0,
                "retry_after": exc.retry_after,
            }
        },
        headers={"Retry-After": str(exc.retry_after)},
    )


async def ai_provider_error_handler(
    request: Request, exc: AIProviderError
) -> JSONResponse:
    if isinstance(exc, AIProviderRateLimitError):
        status_code = 429
    elif isinstance(exc, AIProviderTimeoutError):
        status_code = 504
    elif isinstance(exc, AIProviderAuthError):
        status_code = 502
    else:
        status_code = 502
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, service_error_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_exception_handler(AIProviderError, ai_provider_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

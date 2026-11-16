from fastapi import Request
from fastapi.responses import JSONResponse

from src.utils.exceptions import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
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

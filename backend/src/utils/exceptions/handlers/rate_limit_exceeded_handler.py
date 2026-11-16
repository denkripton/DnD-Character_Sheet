from fastapi import Request
from fastapi.responses import JSONResponse

from src.utils.exceptions import RateLimitExceeded


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

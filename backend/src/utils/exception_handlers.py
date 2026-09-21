from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.utils.exceptions import RateLimitExceeded, ServiceError


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


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, service_error_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

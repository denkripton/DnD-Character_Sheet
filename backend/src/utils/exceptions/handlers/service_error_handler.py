from fastapi import Request
from fastapi.responses import JSONResponse

from src.utils.exceptions import ServiceError


async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )

from typing import Callable

import structlog
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.utils.exceptions import ServiceError


class ErrorHandlingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except (ServiceError, RequestValidationError, StarletteHTTPException):
                raise
            except Exception as exc:
                structlog.get_logger(__name__).critical(
                    "unhandled_error",
                    method=request.method,
                    path=request.url.path,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    exc_info=True,
                )
                raise

        return custom_route_handler
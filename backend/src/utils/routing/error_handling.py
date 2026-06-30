from typing import Callable

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.exceptions import ServiceError
from src.config import logger


class ErrorHandlingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except (ServiceError, RequestValidationError, StarletteHTTPException):
                raise
            except Exception as exc:
                logger.critical(
                    "Unhandled error | %s %s | %s: %s",
                    request.method,
                    request.url.path,
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                )
                raise

        return custom_route_handler
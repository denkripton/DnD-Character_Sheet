import time
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Update


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler,
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        raw_user = getattr(event, "from_user", None)
        user_id = raw_user.id if raw_user is not None else 0
        username = raw_user.username if raw_user is not None else None
        context = {
            "update_type": type(event).__name__,
            "user_id": user_id,
        }
        if username is not None:
            context["username"] = username
        structlog.contextvars.bind_contextvars(**context)
        logger = structlog.get_logger("app.middleware")
        started = time.monotonic()
        try:
            result = await handler(event, data)
            logger.info(
                "update_handled",
                duration_ms=round((time.monotonic() - started) * 1000),
            )
            return result
        except Exception:
            logger.error(
                "update_failed",
                duration_ms=round((time.monotonic() - started) * 1000),
            )
            raise
        finally:
            structlog.contextvars.unbind_contextvars(*context)
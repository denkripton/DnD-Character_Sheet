import asyncio

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine
from src.config import settings
from src.modules.health.checks.status import DOWN, UP


async def check_postgres(engine: AsyncEngine) -> str:
    try:
        async with asyncio.timeout(settings.HEALTH_CHECK_TIMEOUT_SECONDS):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except (OSError, SQLAlchemyError) as exc:
        structlog.get_logger("src.modules.health.service").warning(
            "postgres_check_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return DOWN
    return UP

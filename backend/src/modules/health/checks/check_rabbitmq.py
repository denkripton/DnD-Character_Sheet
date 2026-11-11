import asyncio

import structlog
from src.config import settings
from src.infrastructure.rabbitmq.bus import RabbitMQMessageBus
from src.modules.health.checks.status import DOWN, UP
from src.utils.exceptions import RabbitMQConnectionError


async def check_rabbitmq(message_bus: RabbitMQMessageBus) -> str:
    try:
        async with asyncio.timeout(settings.HEALTH_CHECK_TIMEOUT_SECONDS):
            healthy = await message_bus.health_check()
    except (OSError, RabbitMQConnectionError) as exc:
        structlog.get_logger("src.modules.health.service").warning(
            "rabbitmq_check_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return DOWN
    return UP if healthy else DOWN

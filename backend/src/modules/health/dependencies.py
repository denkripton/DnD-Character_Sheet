from fastapi import Request
from src.databases.sql import engine
from src.infrastructure.redis import redis
from src.modules.health.service import HealthService


def get_health_service(request: Request) -> HealthService:
    return HealthService(
        engine=engine,
        redis_client=redis,
        message_bus=request.app.state.message_bus,
    )

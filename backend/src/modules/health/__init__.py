from src.modules.health.dependencies import get_health_service
from src.modules.health.router import router as health_router
from src.modules.health.service import HealthService

__all__ = ["HealthService", "get_health_service", "health_router"]

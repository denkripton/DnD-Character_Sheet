from fastapi import APIRouter
from src.modules.health.router.liveness import router as liveness_router
from src.modules.health.router.readiness import router as readiness_router
from src.utils import ErrorHandlingRoute

router = APIRouter(prefix="/health", route_class=ErrorHandlingRoute)
router.include_router(liveness_router)
router.include_router(readiness_router)

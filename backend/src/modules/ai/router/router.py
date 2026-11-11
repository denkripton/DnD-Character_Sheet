from fastapi import APIRouter
from src.modules.ai.router.list_models import router as models_router
from src.modules.ai.router.list_providers import router as providers_router
from src.utils import ErrorHandlingRoute

router = APIRouter(prefix="/ai", route_class=ErrorHandlingRoute)
router.include_router(models_router)
router.include_router(providers_router)

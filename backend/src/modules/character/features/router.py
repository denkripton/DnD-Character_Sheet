from fastapi import APIRouter
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.features.handlers import (
    add_feature,
    delete_feature,
    generate_features,
    get_features,
    update_feature,
)
from src.modules.character.features.handlers.add_feature import router as add_router
from src.modules.character.features.handlers.delete_feature import (
    router as delete_router,
)
from src.modules.character.features.handlers.generate_features import (
    router as generate_router,
)
from src.modules.character.features.handlers.update_feature import (
    router as update_router,
)
from src.modules.character.features.schemas import FeatureReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/features", route_class=ErrorHandlingRoute
)
router.get(
    "",
    summary="Get all features and traits (Protected)",
    tags=["Features & Traits CRUD's"],
    description="Get all features and traits of one of your characters",
    response_model=list[FeatureReadSchema],
    responses={401: {"model": User401}, 422: {"model": User422}},
)(get_features)
router.include_router(add_router)
router.include_router(generate_router)
router.include_router(update_router)
router.include_router(delete_router)

__all__ = [
    "add_feature",
    "delete_feature",
    "generate_features",
    "get_features",
    "router",
    "update_feature",
]

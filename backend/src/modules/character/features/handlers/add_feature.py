from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.features.dependencies import get_feature_service
from src.modules.character.features.schemas import (
    FeatureCreateSchema,
    FeatureReadSchema,
)
from src.modules.character.features.service import FeatureService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/create",
    summary="Add a feature or trait (Protected)",
    tags=["Features & Traits CRUD's"],
    description="Add a feature or trait to your character",
    response_model=FeatureReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def add_feature(
    character_id: str,
    data: FeatureCreateSchema,
    user_id: str = Depends(get_current_user),
    service: FeatureService = Depends(get_feature_service),
):
    return await service.add_feature(
        user_id=user_id, character_id=character_id, data=data
    )

from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.features.dependencies import get_feature_service
from src.modules.character.features.service import FeatureService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.delete(
    "/{feature_id}",
    summary="Delete a feature (Protected)",
    tags=["Features & Traits CRUD's"],
    description="Delete one of the character's features",
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def delete_feature(
    character_id: str,
    feature_id: str,
    user_id: str = Depends(get_current_user),
    service: FeatureService = Depends(get_feature_service),
):
    return await service.delete_feature(
        user_id=user_id, character_id=character_id, feature_id=feature_id
    )

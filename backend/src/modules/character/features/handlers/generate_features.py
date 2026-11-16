from fastapi import APIRouter, Depends, Query
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.features.dependencies import get_feature_service
from src.modules.character.features.schemas import FeatureReadSchema
from src.modules.character.features.service import FeatureService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/generate",
    summary="Generate random features (Protected)",
    tags=["Features & Traits CRUD's"],
    description=(
        "Add a random set of features and traits (1-3 by default). "
        "Already known features are skipped."
    ),
    response_model=list[FeatureReadSchema],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_features(
    character_id: str,
    count: int | None = Query(
        default=None,
        ge=1,
        le=16,
        description="How many features to generate (default: random 1-3)",
    ),
    user_id: str = Depends(get_current_user),
    service: FeatureService = Depends(get_feature_service),
):
    return await service.generate_features(
        user_id=user_id, character_id=character_id, count=count
    )

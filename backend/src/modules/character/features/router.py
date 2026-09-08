from fastapi import APIRouter, Depends, Query

from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.features.dependencies import get_feature_service
from src.modules.character.features.service import FeatureService
from src.modules.character.features.schemas import FeatureCreateSchema, FeatureReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/features", route_class=ErrorHandlingRoute
)


@router.get(
    "",
    summary="Get all features and traits (Protected)",
    tags=["Features & Traits CRUD's"],
    description="Get all features and traits of one of your characters",
    response_model=list[FeatureReadSchema],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def get_features(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: FeatureService = Depends(get_feature_service),
):
    return await service.get_features(user_id=user_id, character_id=character_id)


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


@router.put(
    "/{feature_id}",
    summary="Update a feature (Protected)",
    tags=["Features & Traits CRUD's"],
    description="Update one of the character's features",
    response_model=FeatureReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def update_feature(
    character_id: str,
    feature_id: str,
    data: FeatureCreateSchema,
    user_id: str = Depends(get_current_user),
    service: FeatureService = Depends(get_feature_service),
):
    return await service.update_feature(
        user_id=user_id, character_id=character_id, feature_id=feature_id, data=data
    )


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
from fastapi import APIRouter, Depends, Query
from typing import Literal

from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.stats.schemas import StatsCreateSchema
from src.modules.character.stats.schemas.response import StatsResponseSchema
from src.modules.character.stats.dependencies import get_stats_service
from src.modules.character.stats.service import StatsService
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/stats", route_class=ErrorHandlingRoute
)


@router.get(
    "",
    summary="Get character stats (Protected)",
    tags=["Stats CRUD's"],
    description="Get stats and modifiers of one of your characters",
    response_model=StatsResponseSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def get_stats(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: StatsService = Depends(get_stats_service),
):
    return await service.get_stats(user_id=user_id, character_id=character_id)


@router.post(
    "/create/generate",
    summary="Generate stats (Protected)",
    tags=["Stats CRUD's"],
    description=(
        "Generate stats for one of your characters. method='random' rolls 4d6 "
        "and drops the lowest die for each score (PHB), method='standard' uses "
        "the standard array 15, 14, 13, 12, 10, 8, method='point_buy' randomly "
        "spends the 27 point buy points (scores 8-15) across the six abilities."
    ),
    response_model=StatsResponseSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_random_stats(
    character_id: str,
    method: Literal["random", "standard", "point_buy"] = Query(
        "random",
        description="Generation method: random (4d6), standard array, or point_buy (27 points)",
    ),
    user_id: str = Depends(get_current_user),
    service: StatsService = Depends(get_stats_service),
):
    return await service.generate_stats(
        user_id=user_id, character_id=character_id, method=method
    )


@router.post(
    "/create",
    summary="Add stats on your own (Protected)",
    tags=["Stats CRUD's"],
    description="Add any stats you want to give your character",
    response_model=StatsResponseSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def add_stats_yourself(
    character_id: str,
    data: StatsCreateSchema,
    user_id: str = Depends(get_current_user),
    service: StatsService = Depends(get_stats_service),
):
    return await service.add_stats(user_id=user_id, character_id=character_id, data=data)
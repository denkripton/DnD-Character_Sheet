from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.stats.dependencies import get_stats_service
from src.modules.character.stats.schemas import StatsCreateSchema
from src.modules.character.stats.schemas.response import StatsResponseSchema
from src.modules.character.stats.service import StatsService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


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

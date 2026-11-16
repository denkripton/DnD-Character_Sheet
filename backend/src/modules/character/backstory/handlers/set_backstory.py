from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.backstory.dependencies import get_backstory_service
from src.modules.character.backstory.schemas import (
    BackstoryCreateSchema,
    BackstoryReadSchema,
)
from src.modules.character.backstory.service import BackstoryService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/create",
    summary="Set or update backstory (Protected)",
    tags=["Backstory CRUD's"],
    description="Set or update the long backstory written by the player",
    response_model=BackstoryReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def set_backstory(
    character_id: str,
    data: BackstoryCreateSchema,
    user_id: str = Depends(get_current_user),
    service: BackstoryService = Depends(get_backstory_service),
):
    return await service.set_backstory(
        user_id=user_id, character_id=character_id, data=data
    )

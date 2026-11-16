from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.base.dependencies import get_character_service
from src.modules.character.base.schemas import (
    CharacterCreateSchema,
    CharacterReadSchema,
)
from src.modules.character.base.service import CharacterService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/create",
    summary="Character creation (Protected)",
    tags=["Character CRUD's"],
    description="Create your character",
    response_model=CharacterReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def create_character(
    data: CharacterCreateSchema,
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service),
):
    return await service.character_creation(user_id=user_id, data=data)

from fastapi import APIRouter, Depends

from src.dependencies import get_error
from src.modules.auth import get_current_user

from src.modules.character.schemas.character.creation import CharacterCreateSchema
from src.modules.character.schemas.character.read import CharacterRead
from src.modules.character.dependencies import get_character_service
from src.modules.character.service import CharacterService

from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422


character_router = APIRouter(prefix="/chatacters")


@character_router.post(
    "/create", 
    summary="Character creation (Protected)",
    tags=["Character CRUD's"],
    description="Create your character",
    response_model=CharacterRead,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def create_character(
    data: CharacterCreateSchema,
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service)
):
    return await get_error(service.character_creation, user_id=user_id, data=data)


@character_router.get(
    "my/",
    summary="Get all your characters (Protected)",
    tags=["Character CRUD's"],
    description="Get all your characters",
    responses={
        401: {"model": User401},
    },
)
async def get_my_charaters(
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service)
):
    return await get_error(service.get_all_charaters, user_id=user_id)
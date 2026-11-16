from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.base.dependencies import get_character_service
from src.modules.character.base.schemas import CharacterReadSchema
from src.modules.character.base.service import CharacterService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.get(
    "/{character_id}",
    summary="Get character by ID (Protected)",
    tags=["Character CRUD's"],
    description="Get a specific character by ID",
    response_model=CharacterReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def character_by_id(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service),
):
    return await service.get_character_by_id(
        user_id=user_id, character_id=character_id
    )

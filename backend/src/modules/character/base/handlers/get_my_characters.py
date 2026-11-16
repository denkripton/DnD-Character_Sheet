from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.character.base.dependencies import get_character_service
from src.modules.character.base.schemas import CharacterReadSchema
from src.modules.character.base.service import CharacterService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.get(
    "/my",
    summary="Get all your characters (Protected)",
    tags=["Character CRUD's"],
    description="Get all your characters",
    response_model=list[CharacterReadSchema],
    responses={
        401: {"model": User401},
    },
)
async def get_my_characters(
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service),
):
    return await service.get_all_characters(user_id=user_id)

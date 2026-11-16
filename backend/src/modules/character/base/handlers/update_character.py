from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.base.dependencies import get_character_service
from src.modules.character.base.schemas import (
    CharacterReadSchema,
    CharacterUpdateSchema,
)
from src.modules.character.base.service import CharacterService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.patch(
    "/{character_id}/update",
    summary="Update character (Protected)",
    tags=["Character CRUD's"],
    description=(
        "Update character fields (e.g. level up). When level/class/species "
        "change, hit dice, max hit points and the proficiency bonus are "
        "automatically recalculated per the PHB."
    ),
    response_model=CharacterReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def update_character(
    character_id: str,
    data: CharacterUpdateSchema,
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service),
):
    return await service.update_character(
        user_id=user_id, character_id=character_id, data=data
    )

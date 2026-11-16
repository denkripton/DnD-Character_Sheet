from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.saving_throws.dependencies import get_saving_throws_service
from src.modules.character.saving_throws.schemas import SavingThrowsReadSchema
from src.modules.character.saving_throws.service import SavingThrowsService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/generate",
    summary="Generate random saving throws (Protected)",
    tags=["Saving Throws CRUD's"],
    description=(
        "Randomly pick 1-2 ability scores the character becomes proficient in "
        "and save them."
    ),
    response_model=SavingThrowsReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_saving_throws(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: SavingThrowsService = Depends(get_saving_throws_service),
):
    return await service.generate_saving_throws(
        user_id=user_id, character_id=character_id
    )

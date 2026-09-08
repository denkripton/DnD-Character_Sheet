from fastapi import APIRouter, Depends

from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.saving_throws.dependencies import get_saving_throws_service
from src.modules.character.saving_throws.service import SavingThrowsService
from src.modules.character.saving_throws.schemas import SavingThrowsCreateSchema, SavingThrowsReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/saving-throws", route_class=ErrorHandlingRoute
)


@router.get(
    "",
    summary="Get saving throws (Protected)",
    tags=["Saving Throws CRUD's"],
    description="Get which saving throws the character is proficient in",
    response_model=SavingThrowsReadSchema | None,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def get_saving_throws(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: SavingThrowsService = Depends(get_saving_throws_service),
):
    return await service.get_saving_throws(user_id=user_id, character_id=character_id)


@router.post(
    "/create",
    summary="Set or update saving throws (Protected)",
    tags=["Saving Throws CRUD's"],
    description="Set which saving throws the character is proficient in",
    response_model=SavingThrowsReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def set_saving_throws(
    character_id: str,
    data: SavingThrowsCreateSchema,
    user_id: str = Depends(get_current_user),
    service: SavingThrowsService = Depends(get_saving_throws_service),
):
    return await service.set_saving_throws(
        user_id=user_id, character_id=character_id, data=data
    )


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
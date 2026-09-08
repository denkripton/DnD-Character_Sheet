from fastapi import APIRouter, Depends

from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.base.dependencies import get_character_service
from src.modules.character.base.service import CharacterService
from src.modules.character.base.schemas import (
    CharacterCreateSchema,
    CharacterReadSchema,
    CharacterUpdateSchema,
)
from src.utils import ErrorHandlingRoute

router = APIRouter(prefix="/chatacters", route_class=ErrorHandlingRoute)


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


@router.post(
    "/generate",
    summary="Generate a random character (Protected)",
    tags=["Character CRUD's"],
    description=(
        "Generate a character with a random name, class, species, alignment "
        "and background, then save it. Returns the created character."
    ),
    response_model=CharacterReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_character(
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service),
):
    return await service.generate_character(user_id=user_id)


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


@router.get(
    "/{character_id}",
    summary="Get character by ID (Protected)",
    tags=["Character CRUD's"],
    description="Get a specific character by ID",
    response_model=CharacterReadSchema,
    responses={
        422: {"model": User422},
    },
)
async def character_by_id(
    character_id: str, service: CharacterService = Depends(get_character_service)
):
    return await service.get_character_by_id(character_id=character_id)


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


@router.delete(
    "/{character_id}/delete",
    summary="Delete character by ID (Protected)",
    tags=["Character CRUD's"],
    description="Delete one of your character",
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def delete_character(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service),
):
    return await service.delete_character(user_id=user_id, character_id=character_id)
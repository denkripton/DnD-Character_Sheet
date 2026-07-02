from typing import List

from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.dependencies import get_character_service
from src.modules.character.schemas import CharacterCreateSchema, CharacterReadSchema
from src.modules.character.service import CharacterService
from src.utils import ErrorHandlingRoute

character_router = APIRouter(prefix="/chatacters", route_class=ErrorHandlingRoute)


@character_router.post(
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


@character_router.get(
    "/my",
    summary="Get all your characters (Protected)",
    tags=["Character CRUD's"],
    description="Get all your characters",
    response_model=List[CharacterReadSchema],
    responses={
        401: {"model": User401},
    },
)
async def get_my_characters(
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service),
):
    return await service.get_all_characters(user_id=user_id)


@character_router.get(
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


@character_router.delete(
    "/{character_id}/delete",
    summary="Delete character by ID (Protected)",
    tags=["Character CRUD's"],
    description="Delete one of your character",
    response_model=CharacterReadSchema,
    responses={
        422: {"model": User422},
    },
)
async def delete_character(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: CharacterService = Depends(get_character_service),
):
    return await service.delete_character(user_id=user_id, character_id=character_id)

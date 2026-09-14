from fastapi import APIRouter, Depends

from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.backstory.dependencies import get_backstory_service
from src.modules.character.backstory.service import BackstoryService
from src.modules.character.backstory.schemas import (
    BackstoryCreateSchema,
    BackstoryReadSchema,
)
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/backstory", route_class=ErrorHandlingRoute
)


@router.get(
    "",
    summary="Get backstory (Protected)",
    tags=["Backstory CRUD's"],
    description="Get the long backstory of the character",
    response_model=BackstoryReadSchema | None,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def get_backstory(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: BackstoryService = Depends(get_backstory_service),
):
    return await service.get_backstory(user_id=user_id, character_id=character_id)


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


@router.post(
    "/generate",
    summary="Generate backstory with Gemini (Protected)",
    tags=["Backstory CRUD's"],
    description=(
        "Generate a long backstory with Gemini using the character's name, "
        "race, class, background, personality and all of its features, then "
        "save it. The 'model' query parameter selects one of the models listed "
        "by GET /ai/models (defaults to the first one). Story must be 500-700 "
        "symbols long; longer than 1000 symbols returns an error."
    ),
    response_model=BackstoryReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_backstory(
    character_id: str,
    model: str | None = None,
    user_id: str = Depends(get_current_user),
    service: BackstoryService = Depends(get_backstory_service),
):
    return await service.generate_backstory(
        user_id=user_id, character_id=character_id, model=model
    )
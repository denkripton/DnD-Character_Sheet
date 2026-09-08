from fastapi import APIRouter, Depends

from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.personality.dependencies import get_personality_service
from src.modules.character.personality.service import PersonalityService
from src.modules.character.personality.schemas import PersonalityCreateSchema, PersonalityReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/personality", route_class=ErrorHandlingRoute
)


@router.get(
    "",
    summary="Get personality (Protected)",
    tags=["Personality CRUD's"],
    description="Get personality traits, ideals, bonds and flaws",
    response_model=PersonalityReadSchema | None,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def get_personality(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: PersonalityService = Depends(get_personality_service),
):
    return await service.get_personality(user_id=user_id, character_id=character_id)


@router.post(
    "/create",
    summary="Set or update personality (Protected)",
    tags=["Personality CRUD's"],
    description="Set personality traits, ideals, bonds and flaws",
    response_model=PersonalityReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def set_personality(
    character_id: str,
    data: PersonalityCreateSchema,
    user_id: str = Depends(get_current_user),
    service: PersonalityService = Depends(get_personality_service),
):
    return await service.set_personality(
        user_id=user_id, character_id=character_id, data=data
    )


@router.post(
    "/generate",
    summary="Generate random personality (Protected)",
    tags=["Personality CRUD's"],
    description=(
        "Generate random personality traits, ideals, bonds and flaws and save "
        "them for the character."
    ),
    response_model=PersonalityReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_personality(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: PersonalityService = Depends(get_personality_service),
):
    return await service.generate_personality(
        user_id=user_id, character_id=character_id
    )
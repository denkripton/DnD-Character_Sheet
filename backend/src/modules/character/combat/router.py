from fastapi import APIRouter, Depends

from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.combat.dependencies import get_combat_service
from src.modules.character.combat.service import CombatService
from src.modules.character.combat.schemas import CombatCreateSchema, CombatReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/combat", route_class=ErrorHandlingRoute
)


@router.get(
    "",
    summary="Get combat info (Protected)",
    tags=["Combat CRUD's"],
    description="Get hit points, armor class, speed, etc.",
    response_model=CombatReadSchema | None,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def get_combat(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: CombatService = Depends(get_combat_service),
):
    return await service.get_combat(user_id=user_id, character_id=character_id)


@router.post(
    "/create",
    summary="Set or update combat info (Protected)",
    tags=["Combat CRUD's"],
    description="Set armor class, hit points, speed, initiative, etc.",
    response_model=CombatReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def set_combat(
    character_id: str,
    data: CombatCreateSchema,
    user_id: str = Depends(get_current_user),
    service: CombatService = Depends(get_combat_service),
):
    return await service.set_combat(
        user_id=user_id, character_id=character_id, data=data
    )


@router.post(
    "/generate",
    summary="Generate random combat info (Protected)",
    tags=["Combat CRUD's"],
    description=(
        "Generate random armor class, initiative, speed and temporary hit "
        "points for a character. Hit dice, max hit points and the proficiency "
        "bonus are still computed from level and stats per the PHB."
    ),
    response_model=CombatReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_combat(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: CombatService = Depends(get_combat_service),
):
    return await service.generate_combat(user_id=user_id, character_id=character_id)
from fastapi import APIRouter, Depends, Query
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.proficiencies.dependencies import get_proficiency_service
from src.modules.character.proficiencies.schemas import ProficiencyReadSchema
from src.modules.character.proficiencies.service import ProficiencyService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/generate",
    summary="Generate random proficiencies (Protected)",
    tags=["Proficiencies CRUD's"],
    description=(
        "Add a random set of armor, weapon, tool proficiencies and languages "
        "(2-4 by default). Already known proficiencies are skipped."
    ),
    response_model=list[ProficiencyReadSchema],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_proficiencies(
    character_id: str,
    count: int | None = Query(
        default=None,
        ge=1,
        le=20,
        description="How many proficiencies to generate (default: random 2-4)",
    ),
    user_id: str = Depends(get_current_user),
    service: ProficiencyService = Depends(get_proficiency_service),
):
    return await service.generate_proficiencies(
        user_id=user_id, character_id=character_id, count=count
    )

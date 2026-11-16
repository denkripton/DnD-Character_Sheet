from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.proficiencies.dependencies import get_proficiency_service
from src.modules.character.proficiencies.schemas import (
    ProficiencyCreateSchema,
    ProficiencyReadSchema,
)
from src.modules.character.proficiencies.service import ProficiencyService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/create",
    summary="Add a proficiency (Protected)",
    tags=["Proficiencies CRUD's"],
    description="Add armor, weapon, tool proficiency or a language",
    response_model=ProficiencyReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def add_proficiency(
    character_id: str,
    data: ProficiencyCreateSchema,
    user_id: str = Depends(get_current_user),
    service: ProficiencyService = Depends(get_proficiency_service),
):
    return await service.add_proficiency(
        user_id=user_id, character_id=character_id, data=data
    )

from fastapi import APIRouter, Depends, Query
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.skills.dependencies import get_skill_service
from src.modules.character.skills.schemas import SkillReadSchema
from src.modules.character.skills.service import SkillService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/generate",
    summary="Generate random skills (Protected)",
    tags=["Skills CRUD's"],
    description=(
        "Add a random set of skills (2-4 by default) to a character. "
        "Already known skills are skipped."
    ),
    response_model=list[SkillReadSchema],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_skills(
    character_id: str,
    count: int | None = Query(
        default=None,
        ge=1,
        le=18,
        description="How many skills to generate (default: random 2-4)",
    ),
    user_id: str = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
):
    return await service.generate_skills(
        user_id=user_id, character_id=character_id, count=count
    )

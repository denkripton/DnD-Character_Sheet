from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.skills.dependencies import get_skill_service
from src.modules.character.skills.service import SkillService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.delete(
    "/{skill_id}",
    summary="Delete a skill (Protected)",
    tags=["Skills CRUD's"],
    description="Delete one of the character's skills",
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def delete_skill(
    character_id: str,
    skill_id: str,
    user_id: str = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
):
    return await service.delete_skill(
        user_id=user_id, character_id=character_id, skill_id=skill_id
    )

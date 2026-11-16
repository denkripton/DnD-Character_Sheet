from fastapi import Depends
from src.modules.auth import get_current_user
from src.modules.character.skills.dependencies import get_skill_service
from src.modules.character.skills.service import SkillService


async def get_skills(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
):
    return await service.get_skills(user_id=user_id, character_id=character_id)

from fastapi import Depends
from src.modules.auth import get_current_user
from src.modules.character.proficiencies.dependencies import get_proficiency_service
from src.modules.character.proficiencies.service import ProficiencyService


async def get_proficiencies(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: ProficiencyService = Depends(get_proficiency_service),
):
    return await service.get_proficiencies(user_id=user_id, character_id=character_id)

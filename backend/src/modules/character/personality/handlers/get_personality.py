from fastapi import Depends
from src.modules.auth import get_current_user
from src.modules.character.personality.dependencies import get_personality_service
from src.modules.character.personality.service import PersonalityService


async def get_personality(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: PersonalityService = Depends(get_personality_service),
):
    return await service.get_personality(user_id=user_id, character_id=character_id)

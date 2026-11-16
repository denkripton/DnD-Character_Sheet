from fastapi import Depends
from src.modules.auth import get_current_user
from src.modules.character.backstory.dependencies import get_backstory_service
from src.modules.character.backstory.service import BackstoryService


async def get_backstory(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: BackstoryService = Depends(get_backstory_service),
):
    return await service.get_backstory(user_id=user_id, character_id=character_id)

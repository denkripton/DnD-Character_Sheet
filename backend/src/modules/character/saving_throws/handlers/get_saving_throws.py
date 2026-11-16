from fastapi import Depends
from src.modules.auth import get_current_user
from src.modules.character.saving_throws.dependencies import get_saving_throws_service
from src.modules.character.saving_throws.service import SavingThrowsService


async def get_saving_throws(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: SavingThrowsService = Depends(get_saving_throws_service),
):
    return await service.get_saving_throws(user_id=user_id, character_id=character_id)

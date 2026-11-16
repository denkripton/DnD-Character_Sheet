from fastapi import Depends
from src.modules.auth import get_current_user
from src.modules.character.stats.dependencies import get_stats_service
from src.modules.character.stats.service import StatsService


async def get_stats(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: StatsService = Depends(get_stats_service),
):
    return await service.get_stats(user_id=user_id, character_id=character_id)

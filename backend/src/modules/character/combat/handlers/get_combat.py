from fastapi import Depends
from src.modules.auth import get_current_user
from src.modules.character.combat.dependencies import get_combat_service
from src.modules.character.combat.service import CombatService


async def get_combat(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: CombatService = Depends(get_combat_service),
):
    return await service.get_combat(user_id=user_id, character_id=character_id)

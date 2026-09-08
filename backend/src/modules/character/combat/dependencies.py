from fastapi import Depends

from src.modules.character.combat.service import CombatService
from src.modules.character.dependencies import (
    character_ownership_guard,
    combat_repository,
    stats_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import CombatRepository, StatsRepository


def get_combat_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    combat_repo: CombatRepository = Depends(combat_repository),
    stats_repo: StatsRepository = Depends(stats_repository),
) -> CombatService:
    return CombatService(
        ownership_guard=ownership,
        combat_repository=combat_repo,
        stats_repository=stats_repo,
    )
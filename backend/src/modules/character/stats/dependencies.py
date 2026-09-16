from fastapi import Depends

from src.dependencies import get_unit_of_work
from src.modules.character.dependencies import (
    character_ownership_guard,
    combat_repository,
    stats_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import CombatRepository, StatsRepository
from src.modules.character.stats.service import StatsService
from src.utils.unit_of_work import UnitOfWork


def get_stats_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    stats_repo: StatsRepository = Depends(stats_repository),
    combat_repo: CombatRepository = Depends(combat_repository),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> StatsService:
    return StatsService(
        ownership_guard=ownership,
        stats_repository=stats_repo,
        combat_repository=combat_repo,
        unit_of_work=uow,
    )
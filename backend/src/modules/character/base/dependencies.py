from fastapi import Depends

from src.modules.auth.repository import UserRepository
from src.modules.auth.dependencies import user_repository
from src.modules.character.base.service import CharacterService
from src.modules.character.dependencies import (
    character_ownership_guard,
    character_repository,
    combat_repository,
    stats_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import (
    CharacterRepository,
    CombatRepository,
    StatsRepository,
)


def get_character_service(
    character_repo: CharacterRepository = Depends(character_repository),
    user_repo: UserRepository = Depends(user_repository),
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    combat_repo: CombatRepository = Depends(combat_repository),
    stats_repo: StatsRepository = Depends(stats_repository),
) -> CharacterService:
    return CharacterService(
        character_repository=character_repo,
        user_repository=user_repo,
        ownership_guard=ownership,
        combat_repository=combat_repo,
        stats_repository=stats_repo,
    )
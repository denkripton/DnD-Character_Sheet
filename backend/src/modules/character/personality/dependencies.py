from fastapi import Depends

from src.dependencies import get_unit_of_work
from src.modules.character.dependencies import (
    character_ownership_guard,
    personality_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.personality.service import PersonalityService
from src.modules.character.repositories import PersonalityRepository
from src.utils.unit_of_work import UnitOfWork


def get_personality_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    personality_repo: PersonalityRepository = Depends(personality_repository),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> PersonalityService:
    return PersonalityService(
        ownership_guard=ownership,
        personality_repository=personality_repo,
        unit_of_work=uow,
    )
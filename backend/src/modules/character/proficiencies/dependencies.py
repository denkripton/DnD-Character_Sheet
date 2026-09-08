from fastapi import Depends

from src.modules.character.dependencies import (
    character_ownership_guard,
    proficiency_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.proficiencies.service import ProficiencyService
from src.modules.character.repositories import ProficiencyRepository


def get_proficiency_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    proficiency_repo: ProficiencyRepository = Depends(proficiency_repository),
) -> ProficiencyService:
    return ProficiencyService(
        ownership_guard=ownership,
        proficiency_repository=proficiency_repo,
    )
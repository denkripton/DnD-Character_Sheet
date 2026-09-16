from fastapi import Depends

from src.dependencies import get_unit_of_work
from src.modules.character.dependencies import (
    character_ownership_guard,
    proficiency_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.proficiencies.service import ProficiencyService
from src.modules.character.repositories import ProficiencyRepository
from src.utils.unit_of_work import UnitOfWork


def get_proficiency_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    proficiency_repo: ProficiencyRepository = Depends(proficiency_repository),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> ProficiencyService:
    return ProficiencyService(
        ownership_guard=ownership,
        proficiency_repository=proficiency_repo,
        unit_of_work=uow,
    )
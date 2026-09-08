from fastapi import Depends

from src.modules.character.dependencies import (
    character_ownership_guard,
    saving_throws_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import SavingThrowsRepository
from src.modules.character.saving_throws.service import SavingThrowsService


def get_saving_throws_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    saving_throws_repo: SavingThrowsRepository = Depends(saving_throws_repository),
) -> SavingThrowsService:
    return SavingThrowsService(
        ownership_guard=ownership,
        saving_throws_repository=saving_throws_repo,
    )
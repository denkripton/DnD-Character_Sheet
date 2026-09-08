from fastapi import Depends

from src.modules.character.dependencies import (
    character_ownership_guard,
    personality_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.personality.service import PersonalityService
from src.modules.character.repositories import PersonalityRepository


def get_personality_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    personality_repo: PersonalityRepository = Depends(personality_repository),
) -> PersonalityService:
    return PersonalityService(
        ownership_guard=ownership,
        personality_repository=personality_repo,
    )
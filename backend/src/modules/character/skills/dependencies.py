from fastapi import Depends

from src.modules.character.dependencies import (
    character_ownership_guard,
    skill_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import SkillRepository
from src.modules.character.skills.service import SkillService


def get_skill_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    skill_repo: SkillRepository = Depends(skill_repository),
) -> SkillService:
    return SkillService(
        ownership_guard=ownership,
        skill_repository=skill_repo,
    )
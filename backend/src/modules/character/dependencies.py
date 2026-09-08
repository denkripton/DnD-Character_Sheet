from fastapi import Depends

from src.dependencies import RepoFactory
from src.modules.auth.dependencies import user_repository
from src.modules.auth.repository import UserRepository
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import (
    CharacterRepository,
    CombatRepository,
    FeatureRepository,
    PersonalityRepository,
    ProficiencyRepository,
    SavingThrowsRepository,
    SkillRepository,
    StatsRepository,
)

character_repository = RepoFactory(repo=CharacterRepository)
stats_repository = RepoFactory(repo=StatsRepository)
combat_repository = RepoFactory(repo=CombatRepository)
saving_throws_repository = RepoFactory(repo=SavingThrowsRepository)
skill_repository = RepoFactory(repo=SkillRepository)
proficiency_repository = RepoFactory(repo=ProficiencyRepository)
feature_repository = RepoFactory(repo=FeatureRepository)
personality_repository = RepoFactory(repo=PersonalityRepository)


def character_ownership_guard(
    character_repo: CharacterRepository = Depends(character_repository),
    user_repo: UserRepository = Depends(user_repository),
) -> CharacterOwnershipGuard:
    return CharacterOwnershipGuard(
        character_repository=character_repo,
        user_repository=user_repo,
    )
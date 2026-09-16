from fastapi import Depends

from src.dependencies import get_unit_of_work
from src.modules.ai import AIGateway, get_ai_client
from src.modules.character.backstory.service import BackstoryService
from src.modules.character.dependencies import (
    backstory_repository,
    character_ownership_guard,
    combat_repository,
    feature_repository,
    personality_repository,
    proficiency_repository,
    saving_throws_repository,
    skill_repository,
    stats_repository,
)
from src.modules.character.repositories import (
    BackstoryRepository,
    CombatRepository,
    FeatureRepository,
    PersonalityRepository,
    ProficiencyRepository,
    SavingThrowsRepository,
    SkillRepository,
    StatsRepository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.utils.unit_of_work import UnitOfWork


def get_backstory_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    backstory_repo: BackstoryRepository = Depends(backstory_repository),
    ai_client: AIGateway = Depends(get_ai_client),
    stats_repo: StatsRepository = Depends(stats_repository),
    combat_repo: CombatRepository = Depends(combat_repository),
    personality_repo: PersonalityRepository = Depends(personality_repository),
    feature_repo: FeatureRepository = Depends(feature_repository),
    skill_repo: SkillRepository = Depends(skill_repository),
    proficiency_repo: ProficiencyRepository = Depends(proficiency_repository),
    saving_throws_repo: SavingThrowsRepository = Depends(saving_throws_repository),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> BackstoryService:
    return BackstoryService(
        ownership_guard=ownership,
        backstory_repository=backstory_repo,
        ai_client=ai_client,
        stats_repository=stats_repo,
        combat_repository=combat_repo,
        personality_repository=personality_repo,
        feature_repository=feature_repo,
        skill_repository=skill_repo,
        proficiency_repository=proficiency_repo,
        saving_throws_repository=saving_throws_repo,
        unit_of_work=uow,
    )
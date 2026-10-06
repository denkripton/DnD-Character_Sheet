from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends
from src.databases.sql import AsyncSessionLocal
from src.dependencies import get_rate_limiter, get_unit_of_work
from src.modules.ai import AIService, get_ai_service
from src.modules.auth.repository import UserRepository
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
    CharacterRepository,
    CombatRepository,
    FeatureRepository,
    PersonalityRepository,
    ProficiencyRepository,
    SavingThrowsRepository,
    SkillRepository,
    StatsRepository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.utils.interfaces.rate_limiter import RateLimiter
from src.utils.unit_of_work import UnitOfWork


def get_backstory_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    backstory_repo: BackstoryRepository = Depends(backstory_repository),
    ai_client: AIService = Depends(get_ai_service),
    stats_repo: StatsRepository = Depends(stats_repository),
    combat_repo: CombatRepository = Depends(combat_repository),
    personality_repo: PersonalityRepository = Depends(personality_repository),
    feature_repo: FeatureRepository = Depends(feature_repository),
    skill_repo: SkillRepository = Depends(skill_repository),
    proficiency_repo: ProficiencyRepository = Depends(proficiency_repository),
    saving_throws_repo: SavingThrowsRepository = Depends(saving_throws_repository),
    uow: UnitOfWork = Depends(get_unit_of_work),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
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
        rate_limiter=rate_limiter,
    )


@asynccontextmanager
async def character_backstory_service_scope() -> AsyncIterator[BackstoryService]:
    async with AsyncSessionLocal() as session:
        yield BackstoryService(
            ownership_guard=CharacterOwnershipGuard(
                character_repository=CharacterRepository(session),
                user_repository=UserRepository(session),
            ),
            backstory_repository=BackstoryRepository(session),
            ai_client=get_ai_service(),
            stats_repository=StatsRepository(session),
            combat_repository=CombatRepository(session),
            personality_repository=PersonalityRepository(session),
            feature_repository=FeatureRepository(session),
            skill_repository=SkillRepository(session),
            proficiency_repository=ProficiencyRepository(session),
            saving_throws_repository=SavingThrowsRepository(session),
            unit_of_work=UnitOfWork(session),
            rate_limiter=get_rate_limiter(),
        )

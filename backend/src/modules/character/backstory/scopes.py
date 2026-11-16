from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from src.databases.sql import AsyncSessionLocal
from src.databases.unit_of_work import UnitOfWork
from src.dependencies import get_rate_limiter
from src.modules.ai import get_ai_service
from src.modules.auth.repository import UserRepository
from src.modules.character.backstory.service import BackstoryService
from src.modules.character.repositories import (
    BackstoryRepository,
    CharacterDraftRepository,
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
            draft_repository=CharacterDraftRepository(session),
        )

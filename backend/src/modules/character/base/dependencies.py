from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends

from src.dependencies import get_rate_limiter, get_unit_of_work
from src.modules.auth.repository import UserRepository
from src.modules.auth.dependencies import user_repository
from src.modules.character.base.service import CharacterService
from src.modules.character.dependencies import (
    character_ownership_guard,
    character_repository,
    combat_repository,
    stats_repository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import (
    CharacterRepository,
    CombatRepository,
    StatsRepository,
)
from src.utils.interfaces.rate_limiter import RateLimiter
from src.databases.unit_of_work import UnitOfWork
from src.databases.sql import AsyncSessionLocal


def get_character_service(
    character_repo: CharacterRepository = Depends(character_repository),
    user_repo: UserRepository = Depends(user_repository),
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    combat_repo: CombatRepository = Depends(combat_repository),
    stats_repo: StatsRepository = Depends(stats_repository),
    uow: UnitOfWork = Depends(get_unit_of_work),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> CharacterService:
    return CharacterService(
        character_repository=character_repo,
        user_repository=user_repo,
        ownership_guard=ownership,
        combat_repository=combat_repo,
        stats_repository=stats_repo,
        unit_of_work=uow,
        rate_limiter=rate_limiter,
    )


@asynccontextmanager
async def character_service_scope() -> AsyncIterator[CharacterService]:
    async with AsyncSessionLocal() as session:
        try:
            characters = CharacterRepository(session)
            users = UserRepository(session)
            yield CharacterService(
                character_repository=characters,
                user_repository=users,
                ownership_guard=CharacterOwnershipGuard(characters, users),
                combat_repository=CombatRepository(session),
                stats_repository=StatsRepository(session),
                unit_of_work=UnitOfWork(session),
                rate_limiter=get_rate_limiter(),
            )
        except Exception:
            await session.rollback()
            raise

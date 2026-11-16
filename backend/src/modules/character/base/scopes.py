from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from src.databases.sql import AsyncSessionLocal
from src.databases.unit_of_work import UnitOfWork
from src.dependencies import get_rate_limiter
from src.modules.auth.repository import UserRepository
from src.modules.character.base.service import CharacterService
from src.modules.character.repositories import (
    CharacterRepository,
    CombatRepository,
    StatsRepository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard


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

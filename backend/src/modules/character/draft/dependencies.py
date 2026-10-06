from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from src.databases.sql import AsyncSessionLocal
from src.dependencies import get_rate_limiter
from src.modules.auth.repository import UserRepository
from src.modules.character.draft.service import CharacterDraftService
from src.modules.character.repositories import (
    CharacterDraftRepository,
    CharacterRepository,
    StatsRepository,
)
from src.utils.unit_of_work import UnitOfWork


@asynccontextmanager
async def character_draft_service_scope() -> AsyncIterator[CharacterDraftService]:
    async with AsyncSessionLocal() as session:
        yield CharacterDraftService(
            draft_repository=CharacterDraftRepository(session),
            character_repository=CharacterRepository(session),
            stats_repository=StatsRepository(session),
            user_repository=UserRepository(session),
            unit_of_work=UnitOfWork(session),
            rate_limiter=get_rate_limiter(),
        )

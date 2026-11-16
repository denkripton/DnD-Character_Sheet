from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from src.databases.sql import AsyncSessionLocal
from src.databases.unit_of_work import UnitOfWork
from src.dependencies import get_rate_limiter
from src.modules.auth.repository import UserRepository
from src.modules.character.repositories import (
    BackstoryRepository,
    CharacterDraftRepository,
    CharacterRepository,
    CombatRepository,
    StatsRepository,
)

if TYPE_CHECKING:
    from src.modules.character.draft.service import CharacterDraftService


logger = structlog.get_logger("src.modules.character.draft.dependencies")


@asynccontextmanager
async def character_draft_service_scope() -> AsyncIterator["CharacterDraftService"]:
    from src.modules.character.draft.service import CharacterDraftService

    async with AsyncSessionLocal() as session:
        try:
            yield CharacterDraftService(
                draft_repository=CharacterDraftRepository(session),
                character_repository=CharacterRepository(session),
                stats_repository=StatsRepository(session),
                user_repository=UserRepository(session),
                unit_of_work=UnitOfWork(session),
                rate_limiter=get_rate_limiter(),
                combat_repository=CombatRepository(session),
                backstory_repository=BackstoryRepository(session),
            )
        except Exception:
            await session.rollback()
            logger.exception("character_draft_transaction_failed")
            raise

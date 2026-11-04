from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import Depends
from src.databases.sql import AsyncSessionLocal
from src.databases.unit_of_work import UnitOfWork
from src.dependencies import get_rate_limiter, get_unit_of_work
from src.modules.auth.dependencies import user_repository
from src.modules.auth.repository import UserRepository
from src.modules.character.repositories import (
    CharacterDraftRepository,
    CharacterRepository,
    CombatRepository,
    StatsRepository,
)
from src.modules.character.dependencies import (
    character_repository,
    combat_repository,
    draft_repository,
    stats_repository,
)
from src.utils.interfaces.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from src.modules.character.draft.service import CharacterDraftService


def get_character_draft_service(
    draft_repository: CharacterDraftRepository = Depends(draft_repository),
    character_repository: CharacterRepository = Depends(character_repository),
    stats_repository: StatsRepository = Depends(stats_repository),
    user_repository: UserRepository = Depends(user_repository),
    unit_of_work: UnitOfWork = Depends(get_unit_of_work),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    combat_repository: CombatRepository = Depends(combat_repository),
) -> "CharacterDraftService":
    from src.modules.character.draft.service import CharacterDraftService

    return CharacterDraftService(
        draft_repository=draft_repository,
        character_repository=character_repository,
        stats_repository=stats_repository,
        user_repository=user_repository,
        unit_of_work=unit_of_work,
        rate_limiter=rate_limiter,
        combat_repository=combat_repository,
    )


@asynccontextmanager
async def character_draft_service_scope() -> AsyncIterator["CharacterDraftService"]:
    from src.modules.character.draft.service import CharacterDraftService

    async with AsyncSessionLocal() as session:
        yield CharacterDraftService(
            draft_repository=CharacterDraftRepository(session),
            character_repository=CharacterRepository(session),
            stats_repository=StatsRepository(session),
            user_repository=UserRepository(session),
            unit_of_work=UnitOfWork(session),
            rate_limiter=get_rate_limiter(),
            combat_repository=CombatRepository(session),
        )

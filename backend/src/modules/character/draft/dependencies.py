from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from src.databases.sql import AsyncSessionLocal
from src.modules.auth.repository import UserRepository
from src.modules.character.draft.service import CharacterDraftService
from src.modules.character.repositories import CharacterDraftRepository
from src.utils.unit_of_work import UnitOfWork


@asynccontextmanager
async def character_draft_service_scope() -> AsyncIterator[CharacterDraftService]:
    async with AsyncSessionLocal() as session:
        yield CharacterDraftService(
            draft_repository=CharacterDraftRepository(session),
            user_repository=UserRepository(session),
            unit_of_work=UnitOfWork(session),
        )

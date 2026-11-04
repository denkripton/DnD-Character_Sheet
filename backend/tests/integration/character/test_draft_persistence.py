import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.databases.sql import Base
from src.databases.unit_of_work import UnitOfWork
from src.modules.auth.models import User
from src.modules.auth.repository import UserRepository
from src.modules.character.base.service import CharacterService
from src.modules.character.draft.service import CharacterDraftService
from src.modules.character.models import CharacterDraft
from src.modules.character.repositories import (
    CharacterDraftRepository,
    CharacterRepository,
    CombatRepository,
    StatsRepository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from tests.utils import StubRateLimiter


def test_saved_character_survives_new_session_and_repeated_save():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            user_id = uuid4()
            async with maker() as session:
                session.add(User(id=user_id, username="hero", email="hero@example.test", password=b"test"))
                await session.commit()

            def service(session):
                return CharacterDraftService(
                    draft_repository=CharacterDraftRepository(session),
                    character_repository=CharacterRepository(session),
                    stats_repository=StatsRepository(session),
                    user_repository=UserRepository(session),
                    unit_of_work=UnitOfWork(session),
                    rate_limiter=StubRateLimiter(),
                    combat_repository=CombatRepository(session),
                )

            async with maker() as session:
                draft_service = service(session)
                draft = await draft_service.create_draft(str(user_id))
                for field, value in (("name", "Aria"), ("kind", "Elf"), ("spec_class", "Wizard")):
                    await draft_service.update_parameter(str(user_id), draft.id, field, value)
                await draft_service.generate_stats(str(user_id), draft.id, "standard")
                assert await CharacterRepository(session).get_many(owner_id=user_id) == []
                first = await draft_service.save_character(str(user_id), draft.id)

            async with maker() as session:
                draft_service = service(session)
                second = await draft_service.save_character(str(user_id), draft.id)
                assert first == second
                characters = await CharacterRepository(session).get_many(owner_id=user_id)
                character_service = CharacterService(
                    character_repository=CharacterRepository(session),
                    user_repository=UserRepository(session),
                    ownership_guard=CharacterOwnershipGuard(
                        CharacterRepository(session), UserRepository(session)
                    ),
                    combat_repository=CombatRepository(session),
                    stats_repository=StatsRepository(session),
                    unit_of_work=UnitOfWork(session),
                    rate_limiter=StubRateLimiter(),
                )
                listed = await character_service.get_all_characters(str(user_id))
                found = await character_service.get_character_by_id(
                    str(user_id), first["character_id"]
                )
                assert len(listed) == 1
                assert found.id == characters[0].id
                assert found.name == "Aria"
                saved_draft = await CharacterDraftRepository(session).get_one(id=draft.id)
                assert isinstance(saved_draft, CharacterDraft)
                assert saved_draft.saved_character_id == characters[0].id

                edit = await draft_service.create_edit_draft(str(user_id), characters[0].id)
                await draft_service.update_parameter(str(user_id), edit.id, "name", "Lyra")
                assert characters[0].name == "Aria"
                await draft_service.delete_draft(str(user_id), edit.id)
                assert characters[0].name == "Aria"

                edit = await draft_service.create_edit_draft(str(user_id), characters[0].id)
                await draft_service.update_parameter(str(user_id), edit.id, "name", "Lyra")
                updated = await draft_service.save_character(str(user_id), edit.id)
                assert updated["character_id"] == first["character_id"]

            async with maker() as session:
                characters = await CharacterRepository(session).get_many(owner_id=user_id)
                assert len(characters) == 1
                assert characters[0].name == "Lyra"
        finally:
            await engine.dispose()

    asyncio.run(scenario())

import asyncio
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.databases.sql import Base
from src.exceptions import ServiceError
from src.modules.auth.models import User
from src.modules.auth.repository import UserRepository
from src.modules.auth.schemas.user.creation import UserCreateSchema
from src.modules.auth.service import UserService
from src.modules.auth.utils.jwt_actions import JWT
from src.modules.character.base.service import CharacterService
from src.modules.character.models import Character, Combat, Stat
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
from src.modules.character.stats.schemas import StatsCreateSchema
from src.modules.character.stats.service import StatsService
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.utils.unit_of_work import UnitOfWork
from tests.utils import (
    FakeRepo,
    FakeUnitOfWork,
    build_guard,
    build_owned_character,
)


class FakeCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl=0):
        pass

    async def delete(self, key):
        pass

    async def delete_pattern(self, pattern):
        pass

    async def exists(self, key):
        return False

    async def scan(self, pattern):
        return


def _build_session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    maker = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    async def open_session():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return maker()

    return open_session, engine


def _run(scenario):
    open_session, engine = _build_session()

    async def wrapper():
        session = await open_session()
        try:
            return await scenario(session, engine)
        finally:
            await session.close()

    try:
        return asyncio.run(wrapper())
    finally:
        asyncio.run(engine.dispose())


CHILD_TABLES = [
    "stats",
    "combat",
    "saving_throws",
    "skills",
    "proficiencies",
    "features",
    "personality",
    "backstories",
]


def _record_statements(engine):
    statements = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    return statements


def _build_character_service(session):
    user_repo = UserRepository(session)
    char_repo = CharacterRepository(session)
    combat_repo = CombatRepository(session)
    stats_repo = StatsRepository(session)
    uow = UnitOfWork(session)
    service = CharacterService(
        character_repository=char_repo,
        user_repository=user_repo,
        ownership_guard=CharacterOwnershipGuard(char_repo, user_repo),
        combat_repository=combat_repo,
        stats_repository=stats_repo,
        unit_of_work=uow,
    )
    return service, user_repo, char_repo


async def _create_user_with_character(session, user_repo, char_repo):
    user = await user_repo.create(username="alice", email="alice@x.y", password=b"h")
    await session.commit()
    character = await char_repo.create(
        name="Grog", spec_class="Barbarian", kind="Human", owner_id=user.id
    )
    await session.commit()
    return user.id, character.id


def test_delete_character_cascades_children_without_lazy_selects():
    def scenario(session, engine):
        service, user_repo, char_repo = _build_character_service(session)
        stats_repo = StatsRepository(session)
        combat_repo = CombatRepository(session)
        saving_throws_repo = SavingThrowsRepository(session)
        personality_repo = PersonalityRepository(session)
        backstory_repo = BackstoryRepository(session)
        skill_repo = SkillRepository(session)
        proficiency_repo = ProficiencyRepository(session)
        feature_repo = FeatureRepository(session)

        async def run():
            conn = await session.connection()
            await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

            user_id, character_id = await _create_user_with_character(
                session, user_repo, char_repo
            )

            await stats_repo.create(
                strength=15, dexterity=14, constitution=15,
                intelligence=8, wisdom=10, charisma=8,
                character_id=character_id,
            )
            await combat_repo.create(
                character_id=character_id,
                max_hp=14, armor_class=14,
                hit_dice_total="1d12", hit_dice_remaining=1,
            )
            await saving_throws_repo.create(
                strength=True, dexterity=False, constitution=True,
                intelligence=False, wisdom=False, charisma=False,
                character_id=character_id,
            )
            await personality_repo.create(
                personality_traits="Brave", ideals="Strength",
                bonds="Clan", flaws="Rage",
                character_id=character_id,
            )
            await backstory_repo.create(backstory="A tale", character_id=character_id)
            await skill_repo.create(
                name="Athletics", ability="strength", character_id=character_id
            )
            await proficiency_repo.create(
                category="weapon", name="Battleaxe", character_id=character_id
            )
            await feature_repo.create(
                name="Rage", description="Enter rage", character_id=character_id
            )
            await session.commit()

            statements = _record_statements(engine)
            statements.clear()

            await service.delete_character(user_id, character_id)

            child_hits = [
                stmt
                for stmt in statements
                if any(f"{table}" in stmt.lower() for table in CHILD_TABLES)
            ]
            assert child_hits == []
            assert not any(
                stmt.lower().startswith("delete") and "characters" not in stmt.lower()
                for stmt in statements
            )

            assert await char_repo.get_by_id(character_id) is None
            assert await stats_repo.get_one(character_id=character_id) is None
            assert await combat_repo.get_one(character_id=character_id) is None
            assert await saving_throws_repo.get_one(character_id=character_id) is None
            assert await personality_repo.get_one(character_id=character_id) is None
            assert await backstory_repo.get_one(character_id=character_id) is None
            assert not await skill_repo.get_many(character_id=character_id)
            assert not await proficiency_repo.get_many(character_id=character_id)
            assert not await feature_repo.get_many(character_id=character_id)

        return run()

    _run(scenario)


def test_stats_character_id_unique_constraint_blocks_duplicates():
    def scenario(session, engine):
        user_repo = UserRepository(session)
        char_repo = CharacterRepository(session)
        stats_repo = StatsRepository(session)

        async def run():
            _, character_id = await _create_user_with_character(
                session, user_repo, char_repo
            )

            await stats_repo.create(
                strength=15, dexterity=14, constitution=15,
                intelligence=8, wisdom=10, charisma=8,
                character_id=character_id,
            )
            await session.commit()

            await stats_repo.create(
                strength=8, dexterity=8, constitution=8,
                intelligence=8, wisdom=8, charisma=8,
                character_id=character_id,
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            rows = await stats_repo.get_many(character_id=character_id)
            assert len(rows) == 1

        return run()

    _run(scenario)


class PendingStatsRepo(FakeRepo):
    async def create(self, **kwargs):
        if kwargs.get("id") is None:
            kwargs["id"] = uuid.uuid4()
        return self.model(**kwargs)


class RaceUnitOfWork(FakeUnitOfWork):
    def __init__(self, repo, conflicting):
        super().__init__()
        self.repo = repo
        self.conflicting = conflicting
        self.first_commit = True

    async def commit(self):
        if self.first_commit:
            self.first_commit = False
            self.repo.rows.append(self.conflicting)
            raise IntegrityError("commit", {}, Exception("duplicate"))
        self.commit_calls += 1


def test_save_stats_recovers_on_concurrent_duplicate(monkeypatch):
    import src.modules.character.stats.service as stats_service

    monkeypatch.setattr(stats_service, "cache", FakeCache())

    char_repo = FakeRepo(model=Character)
    user_repo = FakeRepo(model=User)
    combat_repo = FakeRepo(model=Combat)
    stats_repo = PendingStatsRepo(model=Stat)
    guard = build_guard(char_repo, user_repo, "user-1")
    conflicting = Stat(
        strength=10, dexterity=10, constitution=10,
        intelligence=10, wisdom=10, charisma=10,
        character_id="char-1",
    )
    uow = RaceUnitOfWork(stats_repo, conflicting)
    build_owned_character(char_repo, character_id="char-1", owner_id="user-1")

    service = StatsService(
        ownership_guard=guard,
        stats_repository=stats_repo,
        combat_repository=combat_repo,
        unit_of_work=uow,
    )

    async def flow():
        result = await service.add_stats(
            "user-1",
            "char-1",
            StatsCreateSchema(
                strength=15, dexterity=14, constitution=15,
                intelligence=8, wisdom=10, charisma=8,
            ),
        )
        assert result["stats"]["strength"] == 15
        assert len(stats_repo.rows) == 1
        assert uow.rollback_calls == 1
        assert stats_repo.rows[0].strength == 15

    asyncio.run(flow())


class BlindUserRepository(UserRepository):
    async def get_by_email(self, email):
        return None


def test_register_race_conflict_returns_422_not_500():
    def scenario(session, engine):
        user_repo = BlindUserRepository(session)
        service = UserService(
            user_repository=user_repo, jwt=JWT(), unit_of_work=UnitOfWork(session)
        )

        async def run():
            existing = UserRepository(session)
            await existing.create(
                username="alice", email="alice@x.y", password=b"h"
            )
            await session.commit()

            with pytest.raises(ServiceError) as exc_info:
                await service.register(
                    UserCreateSchema(username="alice", email="alice@x.y", password="som@Th1ng")
                )
            assert exc_info.value.status_code == 422

            rows = await existing.get_many(email="alice@x.y")
            assert len(rows) == 1

        return run()

    _run(scenario)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("n+1 and race regression tests passed")
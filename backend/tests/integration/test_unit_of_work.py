import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.databases.sql import Base
from src.dependencies import get_unit_of_work
from src.modules.auth.models import User
from src.modules.auth.repository import UserRepository
from src.modules.character.models import Character
from src.modules.character.repositories import CharacterRepository
from src.utils.unit_of_work import UnitOfWork


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
        return await scenario(open_session)

    try:
        return asyncio.run(wrapper())
    finally:
        asyncio.run(engine.dispose())


class _SpySession:
    def __init__(self, session):
        self._session = session
        self.rollback_calls = 0

    def __getattr__(self, name):
        return getattr(self._session, name)

    async def rollback(self):
        self.rollback_calls += 1
        await self._session.rollback()


def _make_character(repo, owner_id):
    return repo.create(
        name="Grog",
        spec_class="Barbarian",
        kind="Human",
        owner_id=owner_id,
    )


def _make_user(repo):
    return repo.create(
        username="grog",
        email="grog@example.com",
        password=b"hashed",
    )


def test_repositories_bound_to_models():
    assert UserRepository.model is User
    assert CharacterRepository.model is Character


def test_commit_persists_changes():
    async def scenario(open_session):
        session = await open_session()
        uow = UnitOfWork(session)
        user_repo = UserRepository(session)
        char_repo = CharacterRepository(session)

        user = await _make_user(user_repo)
        await session.flush()
        user_id = user.id

        character = await _make_character(char_repo, owner_id=user_id)
        await session.flush()
        char_id = character.id

        await uow.commit()
        await session.close()

        fresh = await open_session()
        found_user = await UserRepository(fresh).get_by_email("grog@example.com")
        found_char = await CharacterRepository(fresh).get_by_id(char_id)
        assert found_user is not None
        assert found_user.id == user_id
        assert found_char is not None
        assert found_char.id == char_id
        await fresh.close()

    _run(scenario)


def test_rollback_discards_changes():
    async def scenario(open_session):
        session = await open_session()
        uow = UnitOfWork(session)
        user_repo = UserRepository(session)
        char_repo = CharacterRepository(session)

        user = await _make_user(user_repo)
        await session.flush()
        user_id = user.id

        character = await _make_character(char_repo, owner_id=user_id)
        await session.flush()
        char_id = character.id

        await uow.rollback()
        await session.close()

        fresh = await open_session()
        found_user = await UserRepository(fresh).get_by_email("grog@example.com")
        found_char = await CharacterRepository(fresh).get_by_id(char_id)
        assert found_user is None
        assert found_char is None
        await fresh.close()

    _run(scenario)


def test_repository_operations_run_inside_transaction():
    async def scenario(open_session):
        session = await open_session()
        uow = UnitOfWork(session)
        user_repo = UserRepository(session)
        char_repo = CharacterRepository(session)

        user = await _make_user(user_repo)
        await session.flush()
        character = await _make_character(char_repo, owner_id=user.id)
        await session.flush()
        char_id = character.id
        assert char_id is not None
        assert await user_repo.get_by_email("grog@example.com") is not None
        assert await char_repo.get_by_id(char_id) is not None

        await uow.rollback()
        await session.close()

        fresh = await open_session()
        assert await CharacterRepository(fresh).get_by_id(char_id) is None
        await fresh.close()

    _run(scenario)


def test_dependency_rolls_back_on_exception():
    async def scenario(open_session):
        raw = await open_session()
        session = _SpySession(raw)
        gen = get_unit_of_work(session)
        await gen.__anext__()

        user_repo = UserRepository(raw)
        char_repo = CharacterRepository(raw)

        user = await _make_user(user_repo)
        await raw.flush()

        character = await _make_character(char_repo, owner_id=user.id)
        await raw.flush()
        char_id = character.id

        with pytest.raises(RuntimeError):
            await gen.athrow(RuntimeError("boom"))

        assert session.rollback_calls == 1
        await raw.close()

        fresh = await open_session()
        assert await CharacterRepository(fresh).get_by_id(char_id) is None
        await fresh.close()

    _run(scenario)
import asyncio
import uuid

CHAR_ID = uuid.uuid4()

import pytest

from src.exceptions import ServiceError
from src.modules.character.models import Character, SavingThrows
from src.modules.character.saving_throws.schemas import SavingThrowsCreateSchema
from src.modules.character.saving_throws.service import SavingThrowsService
from tests.utils import FakeRepo, FakeUnitOfWork, build_guard, build_owned_character


class DummyUser:
    def __init__(self, id):
        self.id = id


def _build():
    user_repo = FakeRepo(model=DummyUser)
    character_repo = FakeRepo(model=Character)
    guard = build_guard(character_repo, user_repo, "user-1")
    build_owned_character(character_repo, CHAR_ID)
    uow = FakeUnitOfWork()
    service = SavingThrowsService(
        ownership_guard=guard,
        saving_throws_repository=FakeRepo(model=SavingThrows),
        unit_of_work=uow,
    )
    return service, "user-1", CHAR_ID


def test_get_saving_throws_none_when_absent():
    service, user_id, char_id = _build()

    async def flow():
        assert await service.get_saving_throws(user_id, char_id) is None

    asyncio.run(flow())


def test_generate_saving_throws_saves():
    service, user_id, char_id = _build()

    async def flow():
        result = await service.generate_saving_throws(user_id, char_id)
        keys = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")
        assert 1 <= sum(getattr(result, key) for key in keys) <= 2

    asyncio.run(flow())


def test_set_saving_throws_creates():
    service, user_id, char_id = _build()

    async def flow():
        created = await service.set_saving_throws(
            user_id, char_id, SavingThrowsCreateSchema(strength=True, dexterity=True)
        )
        assert created.strength is True
        assert created.dexterity is True
        assert created.intelligence is False

    asyncio.run(flow())


def test_set_saving_throws_updates_existing():
    service, user_id, char_id = _build()

    async def flow():
        await service.set_saving_throws(
            user_id, char_id, SavingThrowsCreateSchema(strength=True, dexterity=True)
        )
        updated = await service.set_saving_throws(
            user_id, char_id, SavingThrowsCreateSchema(strength=True, wisdom=True)
        )
        assert updated.strength is True
        assert updated.wisdom is True
        assert updated.dexterity is False

        fetched = await service.get_saving_throws(user_id, char_id)
        assert fetched.strength is True
        assert fetched.wisdom is True
        assert fetched.dexterity is False

    asyncio.run(flow())


def test_get_saving_throws_missing_character_raises():
    service, user_id, _ = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.get_saving_throws(user_id, "missing")
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_create_schema_defaults_to_false():
    schema = SavingThrowsCreateSchema()
    assert schema.strength is False
    assert schema.wisdom is False


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("saving throws service tests passed")
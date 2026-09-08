import asyncio
import uuid

CHAR_ID = uuid.uuid4()

import pytest

from src.exceptions import ServiceError
from src.modules.character.models import Character, Personality
from src.modules.character.personality.schemas import PersonalityCreateSchema
from src.modules.character.personality.service import PersonalityService
from tests.utils import FakeRepo, build_guard, build_owned_character


class DummyUser:
    def __init__(self, id):
        self.id = id


def _build():
    user_repo = FakeRepo(model=DummyUser)
    character_repo = FakeRepo(model=Character)
    guard = build_guard(character_repo, user_repo, "user-1")
    build_owned_character(character_repo, CHAR_ID)
    service = PersonalityService(
        ownership_guard=guard, personality_repository=FakeRepo(model=Personality)
    )
    return service, "user-1", CHAR_ID


def test_get_personality_none_when_absent():
    service, user_id, char_id = _build()

    async def flow():
        assert await service.get_personality(user_id, char_id) is None

    asyncio.run(flow())


def test_set_personality_creates():
    service, user_id, char_id = _build()

    async def flow():
        created = await service.set_personality(
            user_id, char_id, PersonalityCreateSchema(personality_traits="Brave")
        )
        assert created.personality_traits == "Brave"
        assert created.ideals == ""

    asyncio.run(flow())


def test_set_personality_updates_existing():
    service, user_id, char_id = _build()

    async def flow():
        await service.set_personality(
            user_id, char_id, PersonalityCreateSchema(personality_traits="Brave")
        )
        updated = await service.set_personality(
            user_id, char_id, PersonalityCreateSchema(ideals="Strength")
        )
        assert updated.personality_traits == ""
        assert updated.ideals == "Strength"

        full = await service.set_personality(
            user_id, char_id, PersonalityCreateSchema(personality_traits="Brave", ideals="Strength")
        )
        assert full.personality_traits == "Brave"
        assert full.ideals == "Strength"

        fetched = await service.get_personality(user_id, char_id)
        assert fetched.personality_traits == "Brave"
        assert fetched.ideals == "Strength"

    asyncio.run(flow())


def test_get_personality_missing_character_raises():
    service, user_id, _ = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.get_personality(user_id, "missing")
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_create_schema_defaults_to_empty():
    schema = PersonalityCreateSchema()
    assert schema.personality_traits == ""
    assert schema.bonds == ""


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("personality service tests passed")
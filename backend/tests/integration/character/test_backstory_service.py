import asyncio
import uuid

CHAR_ID = uuid.uuid4()

import pytest
from pydantic import ValidationError

from src.exceptions import ServiceError
from src.modules.character.backstory.schemas import BackstoryCreateSchema
from src.modules.character.backstory.service import BackstoryService
from src.modules.character.models import (
    Backstory,
    Character,
    Combat,
    Feature,
    Personality,
    Proficiency,
    SavingThrows,
    Skill,
    Stat,
)
from tests.utils import FakeRepo, build_guard, build_owned_character


class FakeAI:
    def __init__(self, text="A wandering hero seeks an ancient artifact."):
        self.text = text
        self.calls = []

    async def generate(self, prompt, model=None):
        self.calls.append({"prompt": prompt, "model": model})
        return self.text


class DummyUser:
    def __init__(self, id):
        self.id = id


def _build(text="A wandering hero seeks an ancient artifact."):
    user_repo = FakeRepo(model=DummyUser)
    character_repo = FakeRepo(model=Character)
    guard = build_guard(character_repo, user_repo, "user-1")
    character = build_owned_character(character_repo, CHAR_ID)
    character.background = "Soldier"

    ai = FakeAI(text=text)
    service = BackstoryService(
        ownership_guard=guard,
        backstory_repository=FakeRepo(model=Backstory),
        ai_client=ai,
        stats_repository=FakeRepo(model=Stat),
        combat_repository=FakeRepo(model=Combat),
        personality_repository=FakeRepo(model=Personality),
        feature_repository=FakeRepo(model=Feature),
        skill_repository=FakeRepo(model=Skill),
        proficiency_repository=FakeRepo(model=Proficiency),
        saving_throws_repository=FakeRepo(model=SavingThrows),
    )
    return service, "user-1", CHAR_ID, ai


def test_get_backstory_none_when_absent():
    service, user_id, char_id, _ = _build()

    async def flow():
        assert await service.get_backstory(user_id, char_id) is None

    asyncio.run(flow())


def test_set_backstory_creates():
    service, user_id, char_id, _ = _build()

    async def flow():
        created = await service.set_backstory(
            user_id, char_id, BackstoryCreateSchema(backstory="My hero is a wanderer.")
        )
        assert created.backstory == "My hero is a wanderer."

    asyncio.run(flow())


def test_set_backstory_updates_existing():
    service, user_id, char_id, _ = _build()

    async def flow():
        await service.set_backstory(
            user_id, char_id, BackstoryCreateSchema(backstory="First version.")
        )
        updated = await service.set_backstory(
            user_id, char_id, BackstoryCreateSchema(backstory="Second version.")
        )
        assert updated.backstory == "Second version."

        fetched = await service.get_backstory(user_id, char_id)
        assert fetched.backstory == "Second version."

    asyncio.run(flow())


def test_generate_backstory_saves_and_uses_character_context():
    service, user_id, char_id, ai = _build()
    service.personality_repo.rows.append(
        Personality(personality_traits="Brave", character_id=CHAR_ID)
    )
    service.feature_repo.rows.append(
        Feature(name="Rage", description="Deals extra damage", character_id=CHAR_ID)
    )
    service.skill_repo.rows.append(
        Skill(name="Athletics", ability="strength", proficiency=True, character_id=CHAR_ID)
    )
    service.stats_repo.rows.append(
        Stat(
            strength=16, dexterity=14, constitution=15,
            intelligence=10, wisdom=12, charisma=8, character_id=CHAR_ID,
        )
    )
    service.proficiency_repo.rows.append(
        Proficiency(category="Armor", name="Shields", character_id=CHAR_ID)
    )
    service.saving_throws_repo.rows.append(SavingThrows(strength=True, character_id=CHAR_ID))

    async def flow():
        result = await service.generate_backstory(user_id, char_id, model="gemini-2.5-flash")
        assert result.backstory == ai.text

        prompt = ai.calls[0]["prompt"]
        assert ai.calls[0]["model"] == "gemini-2.5-flash"
        assert "Name: Grog" in prompt
        assert "Race: Human" in prompt
        assert "Class: Barbarian" in prompt
        assert "Background: Soldier" in prompt
        assert "Brave" in prompt
        assert "Rage" in prompt
        assert "Athletics" in prompt
        assert "Shields" in prompt

    asyncio.run(flow())


def test_generate_backstory_delegates_default_model_choice():
    service, user_id, char_id, ai = _build()

    async def flow():
        await service.generate_backstory(user_id, char_id)
        assert ai.calls[0]["model"] is None

    asyncio.run(flow())


def test_generate_backstory_too_big_raises():
    service, user_id, char_id, _ = _build(text="x" * 1000)

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.generate_backstory(user_id, char_id)
        assert exc_info.value.status_code == 422
        assert exc_info.value.message == "Back story is too big"

    asyncio.run(flow())


def test_generate_backstory_empty_raises():
    service, user_id, char_id, _ = _build(text="")

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.generate_backstory(user_id, char_id)
        assert exc_info.value.status_code == 422
        assert exc_info.value.message == "Empty back story"

    asyncio.run(flow())


def test_get_backstory_missing_character_raises():
    service, user_id, _, _ = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.get_backstory(user_id, "missing")
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_create_schema_requires_text():
    with pytest.raises(ValidationError):
        BackstoryCreateSchema()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("backstory service tests passed")
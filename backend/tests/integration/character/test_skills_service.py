import asyncio
import uuid

CHAR_ID = uuid.uuid4()

import pytest
from pydantic import ValidationError

from src.utils.exceptions import ServiceError
from src.modules.character.models import Character, Skill
from src.modules.character.skills.schemas import SkillAbility, SkillCreateSchema
from src.modules.character.skills.service import SkillService
from tests.utils import FakeRepo, FakeUnitOfWork, build_guard, build_owned_character


class DummyUser:
    def __init__(self, id):
        self.id = id


def _build(owner_id="user-1"):
    user_repo = FakeRepo(model=DummyUser)
    character_repo = FakeRepo(model=Character)
    repo = FakeRepo(model=Skill)
    guard = build_guard(character_repo, user_repo, "user-1")
    build_owned_character(character_repo, CHAR_ID, owner_id)
    uow = FakeUnitOfWork()
    service = SkillService(ownership_guard=guard, skill_repository=repo, unit_of_work=uow)
    return service, repo, "user-1"


def test_add_skill_creates():
    service, _, user_id = _build()

    async def flow():
        created = await service.add_skill(
            user_id, CHAR_ID, SkillCreateSchema(name="Athletics", ability=SkillAbility.strength)
        )
        assert created.name == "Athletics"
        assert created.ability == "strength"

    asyncio.run(flow())


def test_generate_skills_adds_set_and_skips_existing():
    service, _, user_id = _build()

    async def flow():
        created = await service.generate_skills(user_id, CHAR_ID, count=3)
        assert len(created) == 3
        assert len({skill.name for skill in created}) == 3

        again = await service.generate_skills(user_id, CHAR_ID, count=3)
        assert not ({skill.name for skill in again} & {skill.name for skill in created})

    asyncio.run(flow())


def test_update_skill_changes_fields():
    service, _, user_id = _build()

    async def flow():
        created = await service.add_skill(
            user_id, CHAR_ID, SkillCreateSchema(name="Athletics", ability=SkillAbility.strength)
        )
        updated = await service.update_skill(
            user_id,
            CHAR_ID,
            created.id,
            SkillCreateSchema(name="Acrobatics", ability=SkillAbility.dexterity, proficiency=True),
        )
        assert updated.name == "Acrobatics"
        assert updated.ability == "dexterity"
        assert updated.proficiency is True

    asyncio.run(flow())


def test_update_skill_missing_raises():
    service, _, user_id = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.update_skill(
                user_id, CHAR_ID, "missing", SkillCreateSchema(name="X", ability=SkillAbility.strength)
            )
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_delete_skill_removes():
    service, repo, user_id = _build()

    async def flow():
        created = await service.add_skill(
            user_id, CHAR_ID, SkillCreateSchema(name="Athletics", ability=SkillAbility.strength)
        )
        await service.delete_skill(user_id, CHAR_ID, created.id)
        assert repo.rows == []

    asyncio.run(flow())


def test_get_skills_unowned_character_raises():
    service, _, _ = _build(owner_id="user-2")

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.get_skills("user-1", CHAR_ID)
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_create_schema_rejects_invalid_ability():
    with pytest.raises(ValidationError):
        SkillCreateSchema(name="X", ability="luck")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("skills service tests passed")
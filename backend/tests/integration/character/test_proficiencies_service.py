import asyncio
import uuid

CHAR_ID = uuid.uuid4()

import pytest
from pydantic import ValidationError

from src.utils.exceptions import ServiceError
from src.modules.character.models import Character, Proficiency
from src.modules.character.proficiencies.schemas import ProficiencyCreateSchema
from src.modules.character.proficiencies.service import ProficiencyService
from tests.utils import FakeRepo, FakeUnitOfWork, build_guard, build_owned_character


class DummyUser:
    def __init__(self, id):
        self.id = id


def _build():
    user_repo = FakeRepo(model=DummyUser)
    character_repo = FakeRepo(model=Character)
    repo = FakeRepo(model=Proficiency)
    guard = build_guard(character_repo, user_repo, "user-1")
    build_owned_character(character_repo, CHAR_ID)
    uow = FakeUnitOfWork()
    service = ProficiencyService(
        ownership_guard=guard, proficiency_repository=repo, unit_of_work=uow
    )
    return service, repo, "user-1"


def test_add_proficiency_creates():
    service, _, user_id = _build()

    async def flow():
        created = await service.add_proficiency(
            user_id, CHAR_ID, ProficiencyCreateSchema(category="weapon", name="Battleaxe")
        )
        assert created.name == "Battleaxe"
        assert created.category == "weapon"

    asyncio.run(flow())


def test_generate_proficiencies_adds_set():
    service, _, user_id = _build()

    async def flow():
        created = await service.generate_proficiencies(user_id, CHAR_ID, count=3)
        assert len(created) == 3
        assert len({prof.name for prof in created}) == 3

    asyncio.run(flow())


def test_update_proficiency_changes_fields():
    service, _, user_id = _build()

    async def flow():
        created = await service.add_proficiency(
            user_id, CHAR_ID, ProficiencyCreateSchema(category="weapon", name="Battleaxe")
        )
        updated = await service.update_proficiency(
            user_id,
            CHAR_ID,
            created.id,
            ProficiencyCreateSchema(category="armor", name="Heavy Armor"),
        )
        assert updated.category == "armor"
        assert updated.name == "Heavy Armor"

    asyncio.run(flow())


def test_update_proficiency_missing_raises():
    service, _, user_id = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.update_proficiency(
                user_id, CHAR_ID, "missing", ProficiencyCreateSchema(category="weapon", name="X")
            )
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_delete_proficiency_removes():
    service, repo, user_id = _build()

    async def flow():
        created = await service.add_proficiency(
            user_id, CHAR_ID, ProficiencyCreateSchema(category="weapon", name="Battleaxe")
        )
        result = await service.delete_proficiency(user_id, CHAR_ID, created.id)
        assert result == {"message": "Proficiency has been deleted"}
        assert repo.rows == []

    asyncio.run(flow())


def test_delete_proficiency_missing_raises():
    service, _, user_id = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.delete_proficiency(user_id, CHAR_ID, "missing")
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_create_schema_rejects_empty_name():
    with pytest.raises(ValidationError):
        ProficiencyCreateSchema(category="weapon", name="")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("proficiencies service tests passed")
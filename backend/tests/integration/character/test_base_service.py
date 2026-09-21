import asyncio
import uuid

import pytest
from pydantic import ValidationError

from src.utils.exceptions import ServiceError
from src.modules.character.base.schemas import (
    CharacterCreateSchema,
    CharacterUpdateSchema,
)
from src.modules.character.base.service import CharacterService
from src.modules.character.combat.schemas import CombatCreateSchema
from src.modules.character.combat.service import CombatService
from src.modules.character.models import Character, Combat, Stat
from src.modules.character.stats.schemas import StatsCreateSchema
from src.modules.character.stats.service import StatsService
from tests.utils import (
    FakeRepo,
    FakeUnitOfWork,
    StubRateLimiter,
    build_guard,
    build_owned_character,
)

CHAR_ID = uuid.uuid4()
OTHER_CHAR_ID = uuid.uuid4()
THIRD_CHAR_ID = uuid.uuid4()


class DummyUser:
    def __init__(self, id):
        self.id = id


def _services():
    user_repo = FakeRepo(model=DummyUser)
    character_repo = FakeRepo(model=Character)
    stats_repo = FakeRepo(model=Stat)
    combat_repo = FakeRepo(model=Combat)
    guard = build_guard(character_repo, user_repo, "user-1")
    uow = FakeUnitOfWork()

    base = CharacterService(
        character_repository=character_repo,
        user_repository=user_repo,
        ownership_guard=guard,
        combat_repository=combat_repo,
        stats_repository=stats_repo,
        unit_of_work=uow,
        rate_limiter=StubRateLimiter(),
    )
    stats = StatsService(
        ownership_guard=guard,
        stats_repository=stats_repo,
        combat_repository=combat_repo,
        unit_of_work=uow,
    )
    combat = CombatService(
        ownership_guard=guard,
        combat_repository=combat_repo,
        stats_repository=stats_repo,
        unit_of_work=uow,
    )
    return base, stats, combat, "user-1", combat_repo, character_repo


def _creation_data(**overrides):
    values = {"name": "Grog", "spec_class": "Barbarian", "kind": "Human"}
    values.update(overrides)
    return CharacterCreateSchema(**values)


def _full_stats():
    return StatsCreateSchema(
        strength=15, dexterity=14, constitution=15,
        intelligence=8, wisdom=10, charisma=8,
        background_increase={"increases": {"strength": 2, "wisdom": 1}},
    )


def test_character_creation_creates_and_read():
    base, _, _, user_id, _, _ = _services()

    async def flow():
        created = await base.character_creation(user_id=user_id, data=_creation_data())
        assert created.name == "Grog"
        assert created.level == 1

        fetched = await base.get_character_by_id(created.id)
        assert fetched.id == created.id

    asyncio.run(flow())


def test_generate_character_creates_random():
    base, _, _, user_id, _, _ = _services()

    async def flow():
        created = await base.generate_character(user_id)
        assert created.name
        assert created.spec_class
        assert created.kind
        assert created.alignment
        assert created.background

        fetched = await base.get_character_by_id(created.id)
        assert fetched.id == created.id

    asyncio.run(flow())


def test_character_creation_missing_user_raises():
    base, _, _, _, _, _ = _services()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await base.character_creation(user_id="ghost", data=_creation_data())
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_update_character_level_recalculates_combat():
    base, stats, combat, user_id, combat_repo, _ = _services()

    async def flow():
        created = await base.character_creation(user_id=user_id, data=_creation_data())
        await stats.add_stats(user_id, created.id, _full_stats())
        await combat.set_combat(user_id, created.id, CombatCreateSchema(armor_class=14))

        updated = await base.update_character(
            user_id, created.id, CharacterUpdateSchema(level=5)
        )
        assert updated.level == 5

        row = combat_repo.rows[0]
        assert row.hit_dice_total == "5d12"
        assert row.max_hp == 70
        assert row.proficiency_bonus == 3

    asyncio.run(flow())


def test_update_character_missing_character_raises():
    base, _, _, user_id, _, _ = _services()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await base.update_character(
                user_id, CHAR_ID, CharacterUpdateSchema(name="New")
            )
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_update_character_unowned_raises():
    base, _, _, _, _, character_repo = _services()
    build_owned_character(character_repo, CHAR_ID, owner_id="user-2")

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await base.update_character(
                "user-1", CHAR_ID, CharacterUpdateSchema(name="New")
            )
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_update_character_empty_payload_raises():
    base, _, _, user_id, _, character_repo = _services()
    build_owned_character(character_repo, CHAR_ID)

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await base.update_character(user_id, CHAR_ID, CharacterUpdateSchema())
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_get_all_characters_returns_own_only():
    base, _, _, user_id, _, character_repo = _services()
    build_owned_character(character_repo, CHAR_ID, "user-1")
    build_owned_character(character_repo, OTHER_CHAR_ID, "user-1")
    build_owned_character(character_repo, THIRD_CHAR_ID, "user-2")

    async def flow():
        characters = await base.get_all_characters(user_id)
        assert len(characters) == 2
        assert {c.id for c in characters} == {CHAR_ID, OTHER_CHAR_ID}

    asyncio.run(flow())


def test_get_character_by_id_missing_raises():
    base, _, _, _, _, character_repo = _services()
    build_owned_character(character_repo, CHAR_ID)

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await base.get_character_by_id(OTHER_CHAR_ID)
        assert exc_info.value.status_code == 422

        assert (await base.get_character_by_id(CHAR_ID)).id == CHAR_ID

    asyncio.run(flow())


def test_delete_character_removes():
    base, _, _, user_id, _, character_repo = _services()
    build_owned_character(character_repo, CHAR_ID)

    async def flow():
        result = await base.delete_character(user_id, CHAR_ID)
        assert result == {"message": "Character has been deleted"}
        assert character_repo.rows == []
        with pytest.raises(ServiceError):
            await base.get_character_by_id(CHAR_ID)

    asyncio.run(flow())


def test_delete_character_missing_raises():
    base, _, _, user_id, _, _ = _services()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await base.delete_character(user_id, CHAR_ID)
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_character_create_schema_validates_level():
    assert CharacterCreateSchema(name="Grog", spec_class="Barbarian", kind="Human", level=20).level == 20
    with pytest.raises(ValidationError):
        CharacterCreateSchema(name="Grog", spec_class="Barbarian", kind="Human", level=0)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("base service tests passed")
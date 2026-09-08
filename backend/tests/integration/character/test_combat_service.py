import asyncio
import uuid

CHAR_ID = uuid.uuid4()

import pytest
from pydantic import ValidationError

from src.exceptions import ServiceError
from src.modules.character.combat.schemas import CombatCreateSchema
from src.modules.character.combat.service import CombatService
from src.modules.character.models import Character, Combat, Stat
from src.modules.character.stats.schemas import StatsCreateSchema
from src.modules.character.stats.service import StatsService
from tests.utils import FakeRepo, build_guard, build_owned_character


class DummyUser:
    def __init__(self, id):
        self.id = id


def _build(spec_class="Barbarian", kind="Human"):
    user_repo = FakeRepo(model=DummyUser)
    character_repo = FakeRepo(model=Character)
    stats_repo = FakeRepo(model=Stat)
    combat_repo = FakeRepo(model=Combat)
    guard = build_guard(character_repo, user_repo, "user-1")
    build_owned_character(
        character_repo,
        CHAR_ID,
        "user-1",
        spec_class=spec_class,
        kind=kind,
    )

    stats = StatsService(
        ownership_guard=guard,
        stats_repository=stats_repo,
        combat_repository=combat_repo,
    )
    combat = CombatService(
        ownership_guard=guard,
        combat_repository=combat_repo,
        stats_repository=stats_repo,
    )
    return combat, stats, "user-1", combat_repo


def test_set_combat_creates_with_hit_dice_and_hp():
    combat, stats, user_id, _ = _build()
    char_id = CHAR_ID

    async def flow():
        await stats.add_stats(
            user_id,
            char_id,
            StatsCreateSchema(
                strength=15, dexterity=14, constitution=15,
                intelligence=8, wisdom=10, charisma=8,
            ),
        )
        result = await combat.set_combat(user_id, char_id, CombatCreateSchema(armor_class=14))
        assert result.hit_dice_total == "1d12"
        assert result.max_hp == 14
        assert result.current_hp == 14
        assert result.proficiency_bonus == 2
        assert result.hit_dice_remaining == 1

    asyncio.run(flow())


def test_set_combat_without_stats_uses_zero_constitution():
    combat, _, user_id, _ = _build()

    async def flow():
        result = await combat.set_combat(user_id, CHAR_ID, CombatCreateSchema(armor_class=12))
        assert result.max_hp == 12
        assert result.hit_dice_total == "1d12"

    asyncio.run(flow())


def test_wizard_hit_dice():
    combat, stats, user_id, _ = _build(spec_class="Wizard")

    async def flow():
        await stats.add_stats(
            user_id,
            CHAR_ID,
            StatsCreateSchema(
                strength=8, dexterity=14, constitution=10,
                intelligence=15, wisdom=12, charisma=13,
            ),
        )
        result = await combat.set_combat(user_id, CHAR_ID, CombatCreateSchema(armor_class=10))
        assert result.hit_dice_total == "1d6"
        assert result.max_hp == 6

    asyncio.run(flow())


def test_set_combat_upserts_and_resets_current_hp():
    combat, stats, user_id, _ = _build()

    async def flow():
        await stats.add_stats(
            user_id,
            CHAR_ID,
            StatsCreateSchema(
                strength=15, dexterity=14, constitution=15,
                intelligence=8, wisdom=10, charisma=8,
            ),
        )
        first = await combat.set_combat(
            user_id, CHAR_ID, CombatCreateSchema(armor_class=14, current_hp=5)
        )
        assert first.current_hp == 5

        second = await combat.set_combat(
            user_id, CHAR_ID, CombatCreateSchema(armor_class=16)
        )
        assert second.armor_class == 16
        assert second.current_hp == second.max_hp

    asyncio.run(flow())


def test_get_combat_returns_existing():
    combat, _, user_id, _ = _build()

    async def flow():
        assert await combat.get_combat(user_id, CHAR_ID) is None
        created = await combat.set_combat(user_id, CHAR_ID, CombatCreateSchema(armor_class=14))
        fetched = await combat.get_combat(user_id, CHAR_ID)
        assert fetched.id == created.id

    asyncio.run(flow())


def test_get_combat_missing_character_raises():
    combat, _, user_id, _ = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await combat.get_combat(user_id, "missing")
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_combat_create_schema_validates_armor_class():
    assert CombatCreateSchema(armor_class=14).armor_class == 14
    with pytest.raises(ValidationError):
        CombatCreateSchema(armor_class=256)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("combat service tests passed")
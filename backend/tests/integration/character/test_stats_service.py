import asyncio
import uuid

CHAR_ID = uuid.uuid4()

import pytest
from pydantic import ValidationError

from src.exceptions import ServiceError
from src.modules.character.base.schemas import CharacterUpdateSchema
from src.modules.character.base.service import CharacterService
from src.modules.character.combat.schemas import CombatCreateSchema
from src.modules.character.combat.service import CombatService
from src.modules.character.models import Character, Combat, Stat
from src.modules.character.stats.schemas import StatsCreateSchema
from src.modules.character.stats.service import StatsService
from tests.utils import FakeRepo, build_guard


class DummyUser:
    def __init__(self, id):
        self.id = id


def _build():
    user_repo = FakeRepo(model=DummyUser)
    character_repo = FakeRepo(model=Character)
    stats_repo = FakeRepo(model=Stat)
    combat_repo = FakeRepo(model=Combat)
    guard = build_guard(character_repo, user_repo, "user-1")

    char = Character(
        id=CHAR_ID,
        name="Grog",
        spec_class="Barbarian",
        kind="Human",
        owner_id="user-1",
    )
    character_repo.rows.append(char)

    base = CharacterService(
        character_repository=character_repo,
        user_repository=user_repo,
        ownership_guard=guard,
        combat_repository=combat_repo,
        stats_repository=stats_repo,
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
    return base, stats, combat, "user-1", combat_repo, character_repo


def _point_buy():
    return StatsCreateSchema(
        strength=15, dexterity=14, constitution=15,
        intelligence=8, wisdom=10, charisma=8,
        background_increase={"increases": {"strength": 2, "wisdom": 1}},
    )


def test_add_stats_assigns_point_buy_and_background():
    _, stats, _, user_id, _, _ = _build()

    async def flow():
        result = await stats.add_stats(user_id, CHAR_ID, _point_buy())
        assert result["stats"]["strength"] == 17
        assert result["stats"]["dexterity"] == 14
        assert result["modifiers"]["constitution"] == 2

    asyncio.run(flow())


def test_add_stats_updates_existing_and_recalculates_combat():
    base, stats, combat, user_id, combat_repo, _ = _build()

    async def flow():
        await base.update_character(user_id, CHAR_ID, CharacterUpdateSchema(level=5))
        await stats.add_stats(user_id, CHAR_ID, _point_buy())
        await combat.set_combat(user_id, CHAR_ID, CombatCreateSchema(armor_class=14))
        assert combat_repo.rows[0].max_hp == 70

        await stats.add_stats(
            user_id,
            CHAR_ID,
            StatsCreateSchema(
                strength=15, dexterity=14, constitution=8,
                intelligence=12, wisdom=13, charisma=10,
                background_increase={
                    "increases": {"wisdom": 1, "intelligence": 1, "dexterity": 1}
                },
            ),
        )
        assert combat_repo.rows[0].max_hp == 55

    asyncio.run(flow())


def test_get_stats_returns_stats_and_modifiers():
    _, stats, _, user_id, _, _ = _build()

    async def flow():
        await stats.add_stats(user_id, CHAR_ID, _point_buy())
        result = await stats.get_stats(user_id, CHAR_ID)
        assert result["stats"]["strength"] == 17
        assert result["modifiers"]["constitution"] == 2

    asyncio.run(flow())


def test_get_stats_none_when_absent():
    _, stats, _, user_id, _, _ = _build()

    async def flow():
        result = await stats.get_stats(user_id, CHAR_ID)
        assert result == {"stats": None, "modifiers": None}

    asyncio.run(flow())


def test_get_stats_missing_character_raises():
    _, stats, _, user_id, _, _ = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await stats.get_stats(user_id, "missing")
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_generate_stats_standard_array():
    _, stats, _, user_id, _, _ = _build()

    async def flow():
        result = await stats.generate_stats(user_id, CHAR_ID, method="standard")
        assert result["stats"] == {
            "strength": 15,
            "dexterity": 14,
            "constitution": 13,
            "intelligence": 12,
            "wisdom": 10,
            "charisma": 8,
        }
        assert result["modifiers"]["strength"] == 2

    asyncio.run(flow())


def test_generate_stats_random_in_range():
    _, stats, _, user_id, _, _ = _build()

    async def flow():
        result = await stats.generate_stats(user_id, CHAR_ID, method="random")
        for value in result["stats"].values():
            assert 3 <= value <= 18

    asyncio.run(flow())


def test_create_schema_rejects_score_below_eight():
    with pytest.raises(ValidationError):
        StatsCreateSchema(
            strength=7, dexterity=14, constitution=13,
            intelligence=12, wisdom=10, charisma=8,
        )


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stats service tests passed")
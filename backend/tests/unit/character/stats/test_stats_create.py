from pydantic import ValidationError

from src.modules.character.stats.schemas.create import StatsCreateSchema
from src.modules.character.utils.enums.stats import Stats


def _is_rejected(**kwargs):
    try:
        StatsCreateSchema(**kwargs)
        return False
    except ValidationError:
        return True


def test_point_buy_max_value_is_15():
    assert Stats.STATS_COST.value == {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}


def test_point_buy_points_are_27():
    assert Stats.STATS_POINTS.value == 27


def test_valid_point_buy_accepted():
    schema = StatsCreateSchema(
        strength=15, dexterity=14, constitution=13,
        intelligence=12, wisdom=10, charisma=8,
    )
    assert schema.strength == 15


def test_overspend_rejected():
    assert _is_rejected(
        strength=15, dexterity=15, constitution=15,
        intelligence=15, wisdom=8, charisma=15,
    )


def test_score_above_15_rejected():
    assert _is_rejected(
        strength=16, dexterity=14, constitution=13,
        intelligence=12, wisdom=10, charisma=8,
    )


def test_background_plus2_plus1_accepted():
    schema = StatsCreateSchema(
        strength=15, dexterity=14, constitution=13,
        intelligence=12, wisdom=10, charisma=8,
        background_increase={"increases": {"strength": 2, "wisdom": 1}},
    )
    assert schema.background_increase is not None


def test_background_all_plus1_accepted():
    schema = StatsCreateSchema(
        strength=15, dexterity=14, constitution=13,
        intelligence=12, wisdom=10, charisma=8,
        background_increase={"increases": {"strength": 1, "wisdom": 1, "charisma": 1}},
    )
    assert schema.background_increase is not None


def test_background_two_plus2_rejected():
    assert _is_rejected(
        strength=15, dexterity=14, constitution=13,
        intelligence=12, wisdom=10, charisma=8,
        background_increase={"increases": {"strength": 2, "intelligence": 2}},
    )


def test_background_irregular_distribution_rejected():
    assert _is_rejected(
        strength=15, dexterity=14, constitution=13,
        intelligence=12, wisdom=10, charisma=8,
        background_increase={"increases": {"strength": 2, "wisdom": 2, "charisma": 1}},
    )


def test_background_on_max_point_buy_accepted():
    assert not _is_rejected(
        strength=15, dexterity=15, constitution=15,
        intelligence=8, wisdom=8, charisma=8,
        background_increase={"increases": {"strength": 2, "wisdom": 1}},
    )


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stats tests passed")
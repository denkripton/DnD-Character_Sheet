from src.modules.character.utils.enums.stats import Stats


def test_stats_bonus_values():
    assert Stats.STATS_BONUS.value == {
        8: -1,
        9: -1,
        10: 0,
        11: 0,
        12: 1,
        13: 1,
        14: 2,
        15: 2,
        16: 3,
        17: 3,
    }


def test_stats_cost_values():
    assert Stats.STATS_COST.value == {
        8: 0,
        9: 1,
        10: 2,
        11: 3,
        12: 4,
        13: 5,
        14: 7,
        15: 9,
    }


def test_stats_points():
    assert Stats.STATS_POINTS.value == 27


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stats enums tests passed")
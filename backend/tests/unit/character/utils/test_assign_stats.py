from src.modules.character.utils.assign_stats import assign_stats


def test_assign_full_list():
    result = assign_stats([1, 2, 3, 4, 5, 6])
    assert result == {
        "strength": 1,
        "dexterity": 2,
        "constitution": 3,
        "intelligence": 4,
        "wisdom": 5,
        "charisma": 6,
    }


def test_assign_short_list_leaves_none():
    result = assign_stats([15, 14])
    assert result["strength"] == 15
    assert result["dexterity"] == 14
    assert result["constitution"] is None


def test_assign_extra_values_ignored():
    result = assign_stats([1, 2, 3, 4, 5, 6, 7, 8])
    assert set(result) == {
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    }


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("assign stats tests passed")
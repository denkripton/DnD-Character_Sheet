from src.modules.character.utils.compute_mods import compute_modifiers


def test_standard_modifiers():
    stats = {
        "strength": 15,
        "dexterity": 14,
        "constitution": 10,
        "intelligence": 8,
        "wisdom": 20,
        "charisma": 3,
    }
    assert compute_modifiers(stats) == {
        "strength": 2,
        "dexterity": 2,
        "constitution": 0,
        "intelligence": -1,
        "wisdom": 5,
        "charisma": -4,
    }


def test_empty_dict_returns_none():
    assert compute_modifiers({}) is None


def test_none_values_skipped():
    stats = {"strength": 15, "dexterity": None, "constitution": 12}
    assert compute_modifiers(stats) == {"strength": 2, "constitution": 1}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("compute mods tests passed")
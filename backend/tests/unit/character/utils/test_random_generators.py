from src.modules.character.utils.random_character import (
    ALIGNMENTS,
    BACKGROUNDS,
    KINDS,
    NAMES,
    SPEC_CLASSES,
    generate_random_character,
)
from src.modules.character.utils.random_combat import generate_random_combat
from src.modules.character.utils.random_features import generate_random_features
from src.modules.character.utils.random_personality import generate_random_personality
from src.modules.character.utils.random_proficiencies import generate_random_proficiencies
from src.modules.character.utils.random_saving_throws import (
    SAVING_THROW_KEYS,
    generate_random_saving_throws,
)
from src.modules.character.utils.random_skills import SKILLS, generate_random_skills


def test_generate_random_character_fields():
    payload = generate_random_character()
    assert set(payload) == {"name", "spec_class", "kind", "alignment", "background"}
    assert payload["name"] in NAMES
    assert payload["spec_class"] in SPEC_CLASSES
    assert payload["kind"] in KINDS
    assert payload["alignment"] in ALIGNMENTS
    assert payload["background"] in BACKGROUNDS


def test_generate_random_combat_values_in_range():
    payload = generate_random_combat()
    assert 10 <= payload["armor_class"] <= 18
    assert -1 <= payload["initiative"] <= 7
    assert payload["speed"] in {25, 30, 35}
    assert 0 <= payload["temp_hp"] <= 10
    assert 0 <= payload["bonus_hp"] <= 5


def test_generate_random_saving_throws_picks_one_or_two():
    payload = generate_random_saving_throws()
    assert list(payload) == SAVING_THROW_KEYS
    assert 1 <= sum(payload.values()) <= 2


def test_generate_random_skills_with_count():
    items = generate_random_skills(count=3)
    assert len(items) == 3
    names = {item["name"] for item in items}
    assert len(names) == 3
    for item in items:
        assert (item["name"], item["ability"]) in SKILLS
        assert item["proficiency"] is True


def test_generate_random_skills_excludes_existing():
    items = generate_random_skills(count=5, exclude={"Athletics", "Stealth"})
    names = {item["name"] for item in items}
    assert "Athletics" not in names
    assert "Stealth" not in names


def test_generate_random_proficiencies_with_count():
    items = generate_random_proficiencies(count=3)
    assert len(items) == 3
    for item in items:
        assert {"category", "name"} <= set(item)


def test_generate_random_features_with_count():
    items = generate_random_features(count=2)
    assert len(items) == 2
    for item in items:
        assert item["name"]
        assert item["description"]


def test_generate_random_personality_fields():
    payload = generate_random_personality()
    assert set(payload) == {
        "personality_traits",
        "ideals",
        "bonds",
        "flaws",
    }
    for value in payload.values():
        assert value


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("random generators tests passed")
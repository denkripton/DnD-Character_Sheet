from src.modules.character.utils.hit_points import (
    calculate_max_hit_points,
    get_class_hit_die,
    get_kind_hp_bonus,
    hit_dice_text,
    proficiency_bonus_for_level,
    recalculate_combat_hit_dice,
)


class DummyCombat:
    def __init__(self, bonus_hp=0):
        self.bonus_hp = bonus_hp
        self.hit_dice_total = None
        self.max_hp = None
        self.proficiency_bonus = None
        self.hit_dice_remaining = None


class DummyCharacter:
    def __init__(self, spec_class, kind, level):
        self.spec_class = spec_class
        self.kind = kind
        self.level = level


class DummyStats:
    def __init__(self, constitution):
        self.constitution = constitution


def test_barbarian_hit_die():
    assert get_class_hit_die("barbarian") == 12


def test_fighter_hit_die():
    assert get_class_hit_die("Fighter") == 10


def test_cleric_hit_die():
    assert get_class_hit_die("жрец") == 8


def test_wizard_hit_die():
    assert get_class_hit_die("wizard") == 6


def test_unknown_class_defaults_to_d8():
    assert get_class_hit_die("mystery") == 8


def test_known_kind_has_no_bonus_by_default():
    assert get_kind_hp_bonus("Human") == 0


def test_level_1_barbarian_hp():
    assert calculate_max_hit_points(1, 12, 2) == 14


def test_level_1_wizard_hp():
    assert calculate_max_hit_points(1, 6, 0) == 6


def test_level_5_fighter_hp():
    assert calculate_max_hit_points(5, 10, 2) == 60


def test_flat_bonus_added():
    assert calculate_max_hit_points(1, 8, 1, extra_hit_points=3) == 12


def test_hit_dice_text():
    assert hit_dice_text(1, 10) == "1d10"
    assert hit_dice_text(5, 10) == "5d10"


def test_proficiency_at_level_5():
    assert proficiency_bonus_for_level(5) == 3


def test_proficiency_at_level_20():
    assert proficiency_bonus_for_level(20) == 6


def test_proficiency_below_level_1_defaults():
    assert proficiency_bonus_for_level(0) == 2


def test_recalculate_sets_all_fields():
    combat = DummyCombat()
    character = DummyCharacter(spec_class="barbarian", kind="Human", level=1)
    stats = DummyStats(constitution=15)
    recalculate_combat_hit_dice(combat, character, stats)
    assert combat.hit_dice_total == "1d12"
    assert combat.max_hp == 14
    assert combat.proficiency_bonus == 2
    assert combat.hit_dice_remaining == 1


def test_recalculate_without_stats_uses_zero_con_mod():
    combat = DummyCombat()
    character = DummyCharacter(spec_class="wizard", kind="Human", level=5)
    recalculate_combat_hit_dice(combat, character, None)
    assert combat.hit_dice_total == "5d6"
    assert combat.max_hp == 30
    assert combat.proficiency_bonus == 3


def test_recalculate_adds_flat_bonus_hp():
    combat = DummyCombat(bonus_hp=5)
    character = DummyCharacter(spec_class="fighter", kind="Human", level=2)
    stats = DummyStats(constitution=10)
    recalculate_combat_hit_dice(combat, character, stats)
    assert combat.max_hp == 25


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("hit points tests passed")
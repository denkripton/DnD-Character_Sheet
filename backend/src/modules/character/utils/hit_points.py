from typing import Optional

ABILITY_NAMES = {
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
}

CLASS_HIT_DICE = {
    "barbarian": 12,
    "варвар": 12,
    "fighter": 10,
    "воин": 10,
    "paladin": 10,
    "паладин": 10,
    "ranger": 10,
    "следопыт": 10,
    "bard": 8,
    "бард": 8,
    "cleric": 8,
    "жрец": 8,
    "druid": 8,
    "друид": 8,
    "monk": 8,
    "монах": 8,
    "rogue": 8,
    "плут": 8,
    "warlock": 8,
    "колдун": 8,
    "sorcerer": 6,
    "чародей": 6,
    "wizard": 6,
    "волшебник": 6,
}

KIND_HP_BONUS = {}

PROFICIENCY_BONUS_BY_LEVEL = {
    1: 2,
    2: 2,
    3: 2,
    4: 2,
    5: 3,
    6: 3,
    7: 3,
    8: 3,
    9: 4,
    10: 4,
    11: 4,
    12: 4,
    13: 5,
    14: 5,
    15: 5,
    16: 5,
    17: 6,
    18: 6,
    19: 6,
    20: 6,
}

DEFAULT_HIT_DIE = 8


def get_class_hit_die(spec_class: str, default: int = DEFAULT_HIT_DIE) -> int:
    if not spec_class:
        return default
    return CLASS_HIT_DICE.get(spec_class.strip().lower(), default)


def get_kind_hp_bonus(kind: str) -> int:
    if not kind:
        return 0
    return KIND_HP_BONUS.get(kind.strip().lower(), 0)


def proficiency_bonus_for_level(level: int, default: int = 2) -> int:
    if not isinstance(level, int) or level < 1:
        return default
    return PROFICIENCY_BONUS_BY_LEVEL.get(level, default)


def hit_dice_text(level: int, die_size: int) -> str:
    return f"{level}d{die_size}"


def calculate_max_hit_points(
    level: int,
    hit_die_size: int,
    constitution_modifier: int,
    extra_hit_points: Optional[int] = None,
) -> int:
    if extra_hit_points is None:
        extra_hit_points = 0
    level = max(level, 1)
    return level * (hit_die_size + constitution_modifier) + extra_hit_points


def recalculate_combat_hit_dice(combat, character, stats) -> None:
    die_size = get_class_hit_die(character.spec_class)
    constitution = getattr(stats, "constitution", None)
    con_mod = (constitution - 10) // 2 if isinstance(constitution, int) else 0

    extra_hp = get_kind_hp_bonus(character.kind)
    if getattr(combat, "bonus_hp", None) is not None:
        extra_hp += combat.bonus_hp

    combat.hit_dice_total = hit_dice_text(character.level, die_size)
    combat.max_hp = calculate_max_hit_points(
        character.level, die_size, con_mod, extra_hit_points=extra_hp
    )
    combat.proficiency_bonus = proficiency_bonus_for_level(character.level)
    combat.hit_dice_remaining = character.level
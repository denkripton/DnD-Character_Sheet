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

DEFAULT_HIT_DIE = 8


def get_class_hit_die(spec_class: str, default: int = DEFAULT_HIT_DIE) -> int:
    if not spec_class:
        return default
    return CLASS_HIT_DICE.get(spec_class.strip().lower(), default)

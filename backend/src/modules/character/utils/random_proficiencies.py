import random

PROFICIENCIES = [
    ("armor", "Light Armor"),
    ("armor", "Medium Armor"),
    ("armor", "Heavy Armor"),
    ("armor", "Shields"),
    ("weapon", "Simple Weapons"),
    ("weapon", "Martial Weapons"),
    ("weapon", "Longsword"),
    ("weapon", "Battleaxe"),
    ("weapon", "Shortbow"),
    ("tool", "Thieves' Tools"),
    ("tool", "Alchemist's Tools"),
    ("tool", "Herbalism Kit"),
    ("tool", "Navigator's Tools"),
    ("tool", "Smith's Tools"),
    ("language", "Common"),
    ("language", "Elvish"),
    ("language", "Dwarvish"),
    ("language", "Draconic"),
    ("language", "Halfling"),
    ("language", "Orc"),
]


def generate_random_proficiencies(
    count: int | None = None, exclude: set[str] | None = None
) -> list[dict]:
    size = count if count is not None else random.randint(2, 4)
    excluded = exclude or set()
    pool = [prof for prof in PROFICIENCIES if prof[1] not in excluded]
    sample = random.sample(pool, min(size, len(pool)))
    return [{"category": category, "name": name} for category, name in sample]
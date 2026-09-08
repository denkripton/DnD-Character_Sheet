import random

SKILLS = [
    ("Acrobatics", "dexterity"),
    ("Animal Handling", "wisdom"),
    ("Arcana", "intelligence"),
    ("Athletics", "strength"),
    ("Deception", "charisma"),
    ("History", "intelligence"),
    ("Insight", "wisdom"),
    ("Intimidation", "charisma"),
    ("Investigation", "intelligence"),
    ("Medicine", "wisdom"),
    ("Nature", "intelligence"),
    ("Perception", "wisdom"),
    ("Performance", "charisma"),
    ("Persuasion", "charisma"),
    ("Religion", "intelligence"),
    ("Sleight of Hand", "dexterity"),
    ("Stealth", "dexterity"),
    ("Survival", "wisdom"),
]


def generate_random_skills(count: int | None = None, exclude: set[str] | None = None) -> list[dict]:
    size = count if count is not None else random.randint(2, 4)
    excluded = exclude or set()
    pool = [skills for skills in SKILLS if skills[0] not in excluded]
    sample = random.sample(pool, min(size, len(pool)))
    return [
        {"name": name, "ability": ability, "proficiency": True}
        for name, ability in sample
    ]
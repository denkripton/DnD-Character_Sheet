import random

FEATURES = [
    ("Rage", "Enter a rage granting bonus damage and resistance."),
    ("Reckless Attack", "Gain advantage on melee attack rolls while foes attack you with advantage."),
    ("Sneak Attack", "Deal extra damage once per turn when you have advantage."),
    ("Cunning Action", "Use a bonus action to Dash, Disengage, or Hide."),
    ("Divine Smite", "Expend a spell slot to unleash radiant damage."),
    ("Wild Shape", "Transform into a beast you have seen before."),
    ("Action Surge", "Take one extra action on your turn."),
    ("Second Wind", "Regain hit points as a bonus action."),
    ("Extra Attack", "Attack twice when you take the Attack action."),
    ("Bardic Inspiration", "Grant allies a bonus die for ability checks and attacks."),
    ("Evasion", "Take no damage from effects that allow a Dexterity saving throw."),
    ("Channel Divinity", "Channel divine power for a class-specific effect."),
    ("Lay on Hands", "Heal others or cure disease with a pool of healing energy."),
    ("Uncanny Dodge", "Halve damage taken from an attack you can see."),
    ("Expertise", "Double your proficiency bonus on chosen skills."),
    ("Turn Undead", "Force undead to flee from your divine presence."),
]


def generate_random_features(
    count: int | None = None, exclude: set[str] | None = None
) -> list[dict]:
    size = count if count is not None else random.randint(1, 3)
    excluded = exclude or set()
    pool = [feature for feature in FEATURES if feature[0] not in excluded]
    sample = random.sample(pool, min(size, len(pool)))
    return [{"name": name, "description": description} for name, description in sample]
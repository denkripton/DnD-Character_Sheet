import random

NAMES = [
    "Aria", "Bjorn", "Cedric", "Dara", "Evelyn", "Fenn", "Grim", "Hazel",
    "Ivan", "Jora", "Kael", "Lyra", "Milo", "Nadia", "Orin", "Petra",
    "Quinn", "Rowan", "Sable", "Thorne",
]

SPEC_CLASSES = [
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk", "Paladin",
    "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
]

KINDS = [
    "Human", "Elf", "Dwarf", "Halfling", "Gnome", "Half-Elf", "Half-Orc",
    "Dragonborn", "Tiefling", "Aasimar", "Goliath",
]

ALIGNMENTS = [
    "Lawful Good", "Neutral Good", "Chaotic Good", "Lawful Neutral",
    "True Neutral", "Chaotic Neutral", "Lawful Evil", "Neutral Evil",
    "Chaotic Evil",
]

BACKGROUNDS = [
    "Acolyte", "Artisan", "Charlatan", "Criminal", "Entertainer", "Farmer",
    "Guard", "Guide", "Hermit", "Merchant", "Noble", "Outlander", "Sage",
    "Sailor", "Scribe", "Soldier", "Urchin", "Wayfarer",
]


def _pick(items: list[str]) -> str:
    return random.choice(items)


def generate_random_character() -> dict:
    return {
        "name": _pick(NAMES),
        "spec_class": _pick(SPEC_CLASSES),
        "kind": _pick(KINDS),
        "alignment": _pick(ALIGNMENTS),
        "background": _pick(BACKGROUNDS),
    }
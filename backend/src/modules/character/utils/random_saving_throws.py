import random

SAVING_THROW_KEYS = [
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
]


def generate_random_saving_throws() -> dict:
    chosen = random.sample(SAVING_THROW_KEYS, random.randint(1, 2))
    return {key: key in chosen for key in SAVING_THROW_KEYS}
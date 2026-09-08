import random


def generate_random_combat() -> dict:
    return {
        "armor_class": random.randint(10, 18),
        "initiative": random.randint(-1, 7),
        "speed": random.choice([25, 30, 30, 35]),
        "temp_hp": random.randint(0, 10),
        "bonus_hp": random.randint(0, 5),
    }
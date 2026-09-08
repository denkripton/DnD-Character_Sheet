import random

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]


def roll_4d6_drop_lowest() -> int:
    dice = sorted(random.randint(1, 6) for _ in range(4))
    return sum(dice[1:])


def generate_random_stats() -> list[int]:
    return [roll_4d6_drop_lowest() for _ in range(6)]


def generate_standard_array() -> list[int]:
    return list(STANDARD_ARRAY)
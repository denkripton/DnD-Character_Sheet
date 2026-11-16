import random


def roll_4d6_drop_lowest() -> int:
    dice = sorted(random.randint(1, 6) for _ in range(4))
    return sum(dice[1:])

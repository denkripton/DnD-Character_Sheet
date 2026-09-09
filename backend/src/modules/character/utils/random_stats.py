import random

from src.modules.character.utils.enums.stats import Stats

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]


def roll_4d6_drop_lowest() -> int:
    dice = sorted(random.randint(1, 6) for _ in range(4))
    return sum(dice[1:])


def generate_random_stats() -> list[int]:
    return [roll_4d6_drop_lowest() for _ in range(6)]


def generate_standard_array() -> list[int]:
    return list(STANDARD_ARRAY)


def generate_point_buy_stats() -> list[int]:
    cost = Stats.STATS_COST.value
    totals = [8] * 6
    remaining = Stats.STATS_POINTS.value

    while remaining > 0:
        candidates = [
            index
            for index, value in enumerate(totals)
            if value < 15 and (cost[value + 1] - cost[value]) <= remaining
        ]
        index = random.choice(candidates)
        increment_cost = cost[totals[index] + 1] - cost[totals[index]]
        totals[index] += 1
        remaining -= increment_cost

    return totals
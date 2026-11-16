import random

from src.modules.character.utils.enums.stats import Stats


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

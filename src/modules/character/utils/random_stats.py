import random

from src.modules.character.utils.enums.stats import Stats


def generate_random_stats():
    stats_pts = Stats.STATS_POINTS.value
    result_stats = []

    for _ in range(5):
        avaible_stats = []
        for stat, cost in Stats.STATS_COST.value.items():
            if stats_pts >= cost:
                avaible_stats.append(stat)

        if not avaible_stats:
            break

        chosen_stat = random.choice(avaible_stats)
        result_stats.append(chosen_stat)
        stats_pts -= Stats.STATS_COST.value[chosen_stat]

    wanted = 8
    max_cost = -1

    for stat, cost in Stats.STATS_COST.value.items():
        if stats_pts >= cost:
            if cost > max_cost:
                wanted = stat
                max_cost = cost

    result_stats.append(wanted)
    return result_stats

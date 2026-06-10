from enum import Enum

from src.modules.character.utils.enums.constants import stats_bonus, stats_cost

class Stats(Enum):
    STATS_BONUS = stats_bonus
    STATS_COST = stats_cost
    STATS_POINTS = 27
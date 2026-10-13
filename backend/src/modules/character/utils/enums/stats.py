from enum import Enum

_STATS_BONUS = {
    8: -1,
    9: -1,
    10: 0,
    11: 0,
    12: 1,
    13: 1,
    14: 2,
    15: 2,
    16: 3,
    17: 3,
}
_STATS_COST = {
    8: 0,
    9: 1,
    10: 2,
    11: 3,
    12: 4,
    13: 5,
    14: 7,
    15: 9,
}


class Stats(Enum):
    STATS_BONUS = _STATS_BONUS
    STATS_COST = _STATS_COST
    STATS_POINTS = 27

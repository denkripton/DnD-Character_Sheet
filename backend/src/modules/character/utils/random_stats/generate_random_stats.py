from src.modules.character.utils.random_stats.roll_4d6_drop_lowest import (
    roll_4d6_drop_lowest,
)


def generate_random_stats() -> list[int]:
    return [roll_4d6_drop_lowest() for _ in range(6)]

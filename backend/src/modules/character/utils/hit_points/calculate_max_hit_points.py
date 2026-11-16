def calculate_max_hit_points(
    level: int,
    hit_die_size: int,
    constitution_modifier: int,
    extra_hit_points: int | None = None,
) -> int:
    if extra_hit_points is None:
        extra_hit_points = 0
    level = max(level, 1)
    return level * (hit_die_size + constitution_modifier) + extra_hit_points

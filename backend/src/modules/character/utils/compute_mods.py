def compute_modifiers(stats_dict: dict) -> dict | None:
    """Compute D&D ability modifiers from raw stats.

    Args:
        stats_dict: Mapping of ability names to integer scores.

    Returns:
        Mapping of ability names to their modifiers, or ``None`` if ``stats_dict`` is falsy.
    """
    if not stats_dict:
        return None
    return {
        key: (value - 10) // 2
        for key, value in stats_dict.items()
        if value is not None
    }

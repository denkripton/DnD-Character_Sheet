def compute_modifiers(stats_dict: dict) -> dict | None:
    if not stats_dict:
        return None
    return {
        key: (value - 10) // 2
        for key, value in stats_dict.items()
        if value is not None
    }

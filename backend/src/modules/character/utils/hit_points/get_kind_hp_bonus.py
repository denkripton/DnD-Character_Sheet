KIND_HP_BONUS = {}


def get_kind_hp_bonus(kind: str) -> int:
    if not kind:
        return 0
    return KIND_HP_BONUS.get(kind.strip().lower(), 0)

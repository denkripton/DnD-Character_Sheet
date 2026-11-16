from src.modules.character.utils import assign_stats
from src.utils.exceptions import ServiceError


def _parse_stats_values(values) -> dict:
    if not isinstance(values, (list, tuple)) or len(values) != 6:
        raise ServiceError(
            msg="Enter exactly six values in order: STR DEX CON INT WIS CHA.",
            code=422,
        )
    parsed = []
    for value in values:
        try:
            parsed.append(int(str(value).strip()))
        except (TypeError, ValueError) as exc:
            raise ServiceError(msg="Stats must be whole numbers.", code=422) from exc
    return assign_stats(parsed)

from src.modules.character.draft.fields import STAT_FIELDS
from src.utils.exceptions import ServiceError


def _draft_stats_values(stats) -> dict:
    if not isinstance(stats, dict):
        raise ServiceError(msg="Ability scores are invalid.", code=422)
    values = {}
    for field in STAT_FIELDS:
        value = stats.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 3 <= value <= 20
        ):
            raise ServiceError(
                msg="Ability scores must be whole numbers between 3 and 20.",
                code=422,
            )
        values[field] = value
    return values

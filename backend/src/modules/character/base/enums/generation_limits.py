from enum import Enum

from src.modules.character.base.enums.constants.generation_limits import (
    CHARACTER_GENERATION_DAILY_WINDOW_SECONDS,
    CHARACTER_GENERATION_KEY_PREFIX,
)


class GenerationLimits(Enum):
    KEY_PREFIX = CHARACTER_GENERATION_KEY_PREFIX
    DAILY_WINDOW_SECONDS = CHARACTER_GENERATION_DAILY_WINDOW_SECONDS
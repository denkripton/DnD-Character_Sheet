from enum import Enum


class GenerationLimits(Enum):
    KEY_PREFIX = "character_generation:daily"
    DAILY_WINDOW_SECONDS = 86400

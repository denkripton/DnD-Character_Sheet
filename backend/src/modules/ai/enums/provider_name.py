from enum import Enum

from src.modules.ai.enums.constants.ai import DEFAULT_AI_PROVIDER


class AIProviderName(str, Enum):
    GEMINI = DEFAULT_AI_PROVIDER

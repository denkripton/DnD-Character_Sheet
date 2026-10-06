from enum import Enum

from src.modules.ai.enums.constants.ai import AI_TIMEOUT_SECONDS
from src.modules.ai.enums.provider_name import AIProviderName


class AIProviderDefaults(Enum):
    TIMEOUT_SECONDS = AI_TIMEOUT_SECONDS
    DEFAULT_PROVIDER = AIProviderName.GEMINI

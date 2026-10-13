from enum import Enum

from src.modules.ai.enums.provider_name import AIProviderName


class AIProviderDefaults(Enum):
    TIMEOUT_SECONDS = 30.0
    DEFAULT_PROVIDER = AIProviderName.GEMINI

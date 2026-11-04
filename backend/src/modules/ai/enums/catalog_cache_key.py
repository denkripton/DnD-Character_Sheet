from enum import Enum


class AICatalogCacheKey(str, Enum):
    MODELS = "ai:models:catalog"
    PROVIDERS = "ai:providers:catalog"

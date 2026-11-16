from src.infrastructure.redis import cache
from src.utils.interfaces.cache import CacheRepository


def get_cache() -> CacheRepository:
    return cache

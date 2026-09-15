from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheRepository(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError("Method must be redifined")

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        raise NotImplementedError("Method must be redifined")

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError("Method must be redifined")

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> None:
        raise NotImplementedError("Method must be redifined")

    @abstractmethod
    async def exists(self, key: str) -> bool:
        raise NotImplementedError("Method must be redifined")

    @abstractmethod
    async def scan(self, pattern: str):
        raise NotImplementedError("Method must be redifined")

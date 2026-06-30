from abc import ABC, abstractmethod


class ABCRepository(ABC):
    @abstractmethod
    async def create():
        raise NotImplementedError("Method must be redifined")

    @abstractmethod
    async def get_one():
        raise NotImplementedError("Method must be redifined")

    @abstractmethod
    async def get_many():
        raise NotImplementedError("Method must be redifined")

    @abstractmethod
    async def delete_obj():
        raise NotImplementedError("Method must be redifined")

from abc import ABC, abstractmethod

from src.messaging.interfaces.consumer import MessageConsumer
from src.messaging.interfaces.publisher import MessagePublisher


class MessageBus(MessagePublisher, MessageConsumer, ABC):
    @abstractmethod
    async def start(self) -> None:
        raise NotImplementedError("Method must be redefined")

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError("Method must be redefined")
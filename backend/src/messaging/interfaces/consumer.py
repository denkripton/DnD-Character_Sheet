from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence

from src.messaging.messages import MessageEnvelope

MessageHandler = Callable[[MessageEnvelope], Awaitable[None]]


class MessageConsumer(ABC):
    @abstractmethod
    async def subscribe(
        self,
        queue_name: str,
        routing_keys: Sequence[str],
        handler: MessageHandler,
    ) -> None:
        raise NotImplementedError("Method must be redefined")
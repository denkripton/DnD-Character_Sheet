from abc import ABC, abstractmethod

from src.messaging.messages import MessageEnvelope


class MessagePublisher(ABC):
    @abstractmethod
    async def publish(self, envelope: MessageEnvelope, routing_key: str) -> None:
        raise NotImplementedError("Method must be redefined")
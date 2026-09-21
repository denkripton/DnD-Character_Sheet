from collections.abc import Awaitable, Callable

from src.messaging.enums import MessageType
from src.messaging.interfaces import MessageHandler
from src.messaging.messages import MessageEnvelope
from src.utils.exceptions import UnknownMessageTypeError


class CommandDispatcher:
    def __init__(self):
        self._handlers: dict[str, Callable[[MessageEnvelope], Awaitable[None]]] = {}

    def register(self, message_type: MessageType, handler: MessageHandler) -> None:
        self._handlers[message_type.value] = handler

    async def handle(self, envelope: MessageEnvelope) -> None:
        handler = self._handlers.get(envelope.type)
        if handler is None:
            raise UnknownMessageTypeError(envelope.type)
        await handler(envelope)
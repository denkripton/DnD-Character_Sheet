import time
from collections.abc import Awaitable, Callable

import structlog
import structlog.contextvars

from src.messaging.enums import MessageType
from src.messaging.enums.constants import AUTH_USER_ID_HEADER
from src.messaging.interfaces import MessageHandler
from src.messaging.messages import MessageEnvelope
from src.utils.exceptions import UnknownMessageTypeError
from src.utils.logging.context import reset_request_context, set_request_context


class CommandDispatcher:
    def __init__(self):
        self._handlers: dict[str, Callable[[MessageEnvelope], Awaitable[None]]] = {}

    def register(self, message_type: MessageType, handler: MessageHandler) -> None:
        self._handlers[message_type.value] = handler

    async def handle(self, envelope: MessageEnvelope) -> None:
        handler = self._handlers.get(envelope.type)
        if handler is None:
            raise UnknownMessageTypeError(envelope.type)
        set_request_context(
            str(envelope.message_id),
            str(envelope.correlation_id) if envelope.correlation_id else None,
        )
        user_id = envelope.headers.get(AUTH_USER_ID_HEADER)
        if user_id is not None:
            structlog.contextvars.bind_contextvars(user_id=user_id)
        started = time.monotonic()
        try:
            await handler(envelope)
        except Exception:
            structlog.get_logger(__name__).exception(
                "message_failed",
                message_type=envelope.type,
                message_id=str(envelope.message_id),
                duration_ms=round((time.monotonic() - started) * 1000),
            )
            raise
        else:
            structlog.get_logger(__name__).info(
                "message_handled",
                message_type=envelope.type,
                message_id=str(envelope.message_id),
                duration_ms=round((time.monotonic() - started) * 1000),
            )
        finally:
            structlog.contextvars.unbind_contextvars("user_id")
            reset_request_context()

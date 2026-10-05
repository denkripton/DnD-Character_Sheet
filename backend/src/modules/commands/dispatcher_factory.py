from collections.abc import Awaitable, Callable

from src.messaging.contract import create_message, messaging_route
from src.messaging.dispatcher import CommandDispatcher
from src.messaging.enums import MessageType
from src.messaging.interfaces import MessagePublisher
from src.messaging.messages import MessageEnvelope
from src.messaging.security import require_identity_headers, verify_command


def build_bot_command_dispatcher(
    producer: MessagePublisher,
    secret: str | None = None,
    max_age_seconds: int = 300,
) -> CommandDispatcher:
    dispatcher = CommandDispatcher()
    dispatcher.register(
        MessageType.CHARACTER_GENERATE,
        _require_authenticated(
            _publish_generated_event(producer),
            secret,
            max_age_seconds,
        ),
    )
    return dispatcher


def _require_authenticated(
    handler: Callable[[MessageEnvelope], Awaitable[None]],
    secret: str | None,
    max_age_seconds: int,
) -> Callable[[MessageEnvelope], Awaitable[None]]:
    if not secret:
        return handler

    async def wrapped(envelope: MessageEnvelope) -> None:
        verify_command(envelope, secret, max_age_seconds)
        require_identity_headers(envelope)
        await handler(envelope)

    return wrapped


def _publish_generated_event(producer: MessagePublisher):
    async def handle(envelope) -> None:
        event = create_message(
            MessageType.CHARACTER_GENERATED,
            envelope.payload,
            correlation_id=envelope.correlation_id,
            headers=envelope.headers,
        )
        await producer.publish(event, messaging_route(MessageType.CHARACTER_GENERATED))

    return handle
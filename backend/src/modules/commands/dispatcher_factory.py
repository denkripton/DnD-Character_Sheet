from src.messaging.contract import create_message, messaging_route
from src.messaging.dispatcher import CommandDispatcher
from src.messaging.enums import MessageType
from src.messaging.interfaces import MessagePublisher


def build_bot_command_dispatcher(producer: MessagePublisher) -> CommandDispatcher:
    dispatcher = CommandDispatcher()
    dispatcher.register(
        MessageType.CHARACTER_GENERATE,
        _publish_generated_event(producer),
    )
    return dispatcher


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
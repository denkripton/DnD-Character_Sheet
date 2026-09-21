from uuid import uuid4

from src.messaging.contract import create_message, messaging_route
from src.messaging.enums import MessageType


def test_create_message_sets_contract_fields():
    correlation_id = uuid4()

    message = create_message(
        MessageType.CHARACTER_GENERATE,
        payload={"user_id": 7},
        correlation_id=correlation_id,
        headers={"source": "bot"},
    )

    assert message.type == "character.generate.command"
    assert message.payload == {"user_id": 7}
    assert message.correlation_id == correlation_id
    assert message.headers == {"source": "bot"}


def test_create_message_defaults():
    message = create_message(MessageType.CHARACTER_GENERATE)

    assert message.type == "character.generate.command"
    assert message.payload == {}
    assert message.correlation_id is None
    assert message.headers == {}


def test_messaging_route_derives_command_and_event_bindings():
    assert (
        messaging_route(MessageType.CHARACTER_GENERATE)
        == "commands.character.generate"
    )
    assert (
        messaging_route(MessageType.CHARACTER_CREATED)
        == "events.character.created"
    )


def test_every_message_type_maps_to_a_route():
    for message_type in MessageType:
        route = messaging_route(message_type)
        assert route.startswith(("commands.", "events."))
        assert message_type.value.split(".")[-1] in ("command", "event")
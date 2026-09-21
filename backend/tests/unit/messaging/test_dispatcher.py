import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.messaging.contract import create_message
from src.messaging.dispatcher import CommandDispatcher
from src.messaging.enums import MessageType
from src.modules.commands.dispatcher_factory import build_bot_command_dispatcher
from src.utils.exceptions import UnknownMessageTypeError


def run(coro):
    return asyncio.run(coro)


def test_dispatcher_routes_by_message_type():
    dispatcher = CommandDispatcher()
    handled = []

    async def handler(envelope):
        handled.append(envelope)

    dispatcher.register(MessageType.CHARACTER_CREATE, handler)

    envelope = create_message(MessageType.CHARACTER_CREATE, {"user_id": 1})
    run(dispatcher.handle(envelope))

    assert handled == [envelope]


def test_dispatcher_rejects_unknown_message_type():
    dispatcher = CommandDispatcher()
    async def handler(envelope):
        pass

    dispatcher.register(MessageType.CHARACTER_CREATE, handler)

    envelope = create_message(MessageType.CHARACTER_UPDATE, {"user_id": 1})

    with pytest.raises(UnknownMessageTypeError) as excinfo:
        run(dispatcher.handle(envelope))

    assert excinfo.value.message_type == "character.update.command"


def test_bot_command_dispatcher_proof_of_concept_flows_command_to_event():
    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(producer)
    correlation_id = uuid4()

    command = create_message(
        MessageType.CHARACTER_GENERATE,
        payload={"user_id": 5},
        correlation_id=correlation_id,
        headers={"source": "bot", "retry": "0"},
    )
    run(dispatcher.handle(command))

    producer.publish.assert_awaited_once()
    event, routing_key = producer.publish.await_args.args
    assert event.type == "character.generated.event"
    assert event.payload == {"user_id": 5}
    assert event.correlation_id == correlation_id
    assert event.headers == {"source": "bot", "retry": "0"}
    assert routing_key == "events.character.generated"
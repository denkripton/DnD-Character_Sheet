import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.messaging.contract import create_message
from src.messaging.dispatcher import CommandDispatcher
from src.messaging.enums import MessageType
from src.messaging.enums.constants import (
    AUTH_PROVIDER_HEADER,
    AUTH_PROVIDER_USER_ID_HEADER,
    AUTH_USER_ID_HEADER,
)
from src.modules.commands.dispatcher_factory import build_bot_command_dispatcher
from src.utils.exceptions import MessageAuthenticationError, UnknownMessageTypeError
from tests.utils import FakeRepo, FakeUnitOfWork, StubRateLimiter


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
    from src.modules.character.draft import CharacterDraftService
    from src.modules.character.models import CharacterDraft

    producer = AsyncMock()
    user_repo = FakeRepo(model=type("User", (), {}))
    user_repo.rows.append(type("User", (), {"id": "5"})())
    draft_repo = FakeRepo(model=CharacterDraft)
    draft_id = uuid4()
    draft_repo.rows.append(CharacterDraft(id=draft_id, owner_id="5", data={}))

    @asynccontextmanager
    async def scope():
        yield CharacterDraftService(
            draft_repository=draft_repo,
            user_repository=user_repo,
            unit_of_work=FakeUnitOfWork(),
            rate_limiter=StubRateLimiter(allowed=True),
        )

    dispatcher = build_bot_command_dispatcher(producer, draft_service_scope=scope)
    correlation_id = uuid4()

    command = create_message(
        MessageType.CHARACTER_GENERATE,
        payload={"draft_id": str(draft_id), "method": "standard"},
        correlation_id=correlation_id,
        headers={
            "source": "bot",
            "retry": "0",
            AUTH_PROVIDER_HEADER: "telegram",
            AUTH_PROVIDER_USER_ID_HEADER: "7",
            AUTH_USER_ID_HEADER: "5",
        },
    )
    run(dispatcher.handle(command))

    producer.publish.assert_awaited_once()
    event, routing_key = producer.publish.await_args.args
    assert event.type == "character.generated.event"
    assert event.payload["ok"] is True
    assert event.payload["draft"]["data"]["stats"] is not None
    assert event.correlation_id == correlation_id
    assert event.headers["source"] == "bot"
    assert event.headers["retry"] == "0"
    assert routing_key == "events.character.generated"


def test_bot_command_dispatcher_generate_requires_identity_headers():
    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(producer)
    command = create_message(
        MessageType.CHARACTER_GENERATE,
        payload={"draft_id": str(uuid4()), "method": "standard"},
        correlation_id=uuid4(),
        headers={"source": "bot"},
    )

    with pytest.raises(MessageAuthenticationError):
        run(dispatcher.handle(command))
    producer.publish.assert_not_awaited()
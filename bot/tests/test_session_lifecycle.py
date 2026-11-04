import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from app.api import create_bot, create_dispatcher
from app.config import BotConfig
from app.infrastructure.http.exceptions import BackendAuthError
from app.middlewares.session import SessionMiddleware
from app.modules.auth.schemas.context import AuthContext
from app.modules.backstory.states import BackstoryStates
from app.modules.character.router import handle_cancel, handle_create
from app.modules.character.states import CharacterCreationStates
from app.modules.start.router import handle_start
from app.modules.start.service import StartService
from app.presentation.messages import AUTH_UNAVAILABLE_TEXT
from test_character_creation_handlers import FakeCreationService


def _context(storage, user_id=7, chat_id=None):
    return FSMContext(
        storage=storage,
        key=StorageKey(bot_id=1, chat_id=chat_id or user_id, user_id=user_id),
    )


def _auth_service(user_id=7):
    service = AsyncMock()
    service.authenticate.return_value = AuthContext(
        provider="telegram",
        provider_user_id=str(user_id),
        user_id=f"user-{user_id}",
        username="hero",
        access_token="token",
    )
    return service


def _message(text, user_id=7):
    message = MagicMock(spec=Message)
    message.from_user = SimpleNamespace(id=user_id, username="hero", first_name="Hana")
    message.text = text
    message.chat = SimpleNamespace(type="private")
    message.answer = AsyncMock()
    return message


def _callback(data, user_id=7):
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = SimpleNamespace(id=user_id)
    callback.data = data
    callback.answer = AsyncMock()
    return callback


def test_returning_user_can_create_after_cancel_without_start():
    async def scenario():
        state = _context(MemoryStorage())
        service = FakeCreationService()
        auth_service = _auth_service()
        middleware = SessionMiddleware()
        data = {"state": state, "auth_service": auth_service}

        async def create(message, _):
            await handle_create(message, state, service)

        await middleware(create, _message("/create"), data)
        assert await state.get_state() == CharacterCreationStates.generation_mode.state
        await handle_cancel(_message("/cancel"), state, service)
        assert await state.get_data() == {}
        await middleware(create, _message("/create"), data)
        assert service.starts == 2
        assert service.cancelled == ["draft-1"]
        assert (await state.get_data())["auth"]["user_id"] == "user-7"
        assert auth_service.authenticate.await_count == 2

    asyncio.run(scenario())


def test_start_refreshes_auth_without_losing_unfinished_draft():
    async def scenario():
        state = _context(MemoryStorage())
        auth_service = _auth_service()
        message = _message("/start")
        await handle_start(message, StartService(), auth_service, state)
        await state.update_data(draft_id="draft-1", draft_data={"name": "Aria"})
        await state.set_state(CharacterCreationStates.name)
        await handle_start(message, StartService(), auth_service, state)
        assert auth_service.authenticate.await_count == 2
        assert await state.get_state() == CharacterCreationStates.name.state
        assert (await state.get_data())["draft_data"] == {"name": "Aria"}

    asyncio.run(scenario())


def test_new_workflow_replaces_completed_backstory_context():
    async def scenario():
        state = _context(MemoryStorage())
        auth_service = _auth_service()
        middleware = SessionMiddleware()
        await state.update_data(
            auth=auth_service.authenticate.return_value.model_dump(),
            character_id="char-1",
            backstory="old story",
        )
        await state.set_state(BackstoryStates.character_saved)
        service = FakeCreationService()

        async def create(message, _):
            await handle_create(message, state, service)

        await middleware(
            create, _message("/create"), {"state": state, "auth_service": auth_service}
        )
        assert await state.get_state() == CharacterCreationStates.generation_mode.state
        assert "character_id" not in await state.get_data()
        assert "backstory" not in await state.get_data()
        assert service.starts == 1
        auth_service.authenticate.assert_not_awaited()

    asyncio.run(scenario())


def test_mismatched_user_cannot_reuse_stored_session():
    async def scenario():
        state = _context(MemoryStorage())
        await state.update_data(
            auth=_auth_service().authenticate.return_value.model_dump(),
            draft_id="other-draft",
        )
        await state.set_state(CharacterCreationStates.name)
        auth_service = _auth_service(8)
        handler = AsyncMock()
        await SessionMiddleware()(
            handler,
            _callback("cc:save", user_id=8),
            {"state": state, "auth_service": auth_service},
        )
        assert await state.get_state() is None
        assert "draft_id" not in await state.get_data()
        assert (await state.get_data())["auth"]["provider_user_id"] == "8"
        auth_service.authenticate.assert_awaited_once_with(8)

    asyncio.run(scenario())


def test_start_rejects_stored_context_from_another_user():
    async def scenario():
        state = _context(MemoryStorage())
        await state.update_data(
            auth=_auth_service().authenticate.return_value.model_dump(),
            draft_id="other-draft",
        )
        await state.set_state(CharacterCreationStates.name)
        await handle_start(
            _message("/start", 8), StartService(), _auth_service(8), state
        )
        assert await state.get_state() is None
        assert "draft_id" not in await state.get_data()
        assert (await state.get_data())["auth"]["provider_user_id"] == "8"

    asyncio.run(scenario())


def test_callback_discards_orphaned_flow_before_restoring_auth():
    async def scenario():
        state = _context(MemoryStorage())
        await state.update_data(character_id="char-1")
        await state.set_state(BackstoryStates.character_saved)
        auth_service = _auth_service()
        handler = AsyncMock()
        await SessionMiddleware()(
            handler,
            _callback("bs:start"),
            {"state": state, "auth_service": auth_service},
        )
        assert await state.get_state() is None
        assert "character_id" not in await state.get_data()
        assert (await state.get_data())["auth"]["user_id"] == "user-7"
        handler.assert_awaited_once()

    asyncio.run(scenario())


def test_auth_failure_does_not_dispatch_without_session():
    async def scenario():
        state = _context(MemoryStorage())
        auth_service = _auth_service()
        auth_service.authenticate.side_effect = BackendAuthError("unavailable")
        handler = AsyncMock()
        message = _message("/create")
        await SessionMiddleware()(
            handler, message, {"state": state, "auth_service": auth_service}
        )
        handler.assert_not_awaited()
        message.answer.assert_awaited_once_with(AUTH_UNAVAILABLE_TEXT)
        assert await state.get_data() == {}

    asyncio.run(scenario())


def test_other_users_have_independent_fsm_keys():
    async def scenario():
        storage = MemoryStorage()
        first = _context(storage, 7, chat_id=100)
        second = _context(storage, 8, chat_id=100)
        await first.update_data(draft_id="draft-7")
        assert await second.get_data() == {}
        await second.update_data(draft_id="draft-8")
        await first.clear()
        assert (await second.get_data())["draft_id"] == "draft-8"

    asyncio.run(scenario())


def test_dispatcher_restores_auth_before_create_handler():
    async def scenario():
        config = BotConfig(BOT_TOKEN="12345:test-token")
        dispatcher = create_dispatcher(config, storage=MemoryStorage())
        auth_service = _auth_service()
        dispatcher["auth_service"] = auth_service
        received = []

        async def probe(message, state):
            received.append((await state.get_data())["auth"]["user_id"])

        dispatcher.message.register(probe, Command("create"))
        bot = create_bot(config)
        update = Update(
            update_id=1,
            message=Message(
                message_id=1,
                date=datetime.now(UTC),
                chat=Chat(id=7, type="private"),
                from_user=User(id=7, is_bot=False, first_name="Hana"),
                text="/create",
            ),
        )
        await dispatcher.feed_update(bot, update)
        assert received == ["user-7"]
        auth_service.authenticate.assert_awaited_once_with(7)
        await bot.session.close()

    asyncio.run(scenario())

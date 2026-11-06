from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import BotConfig
from app.infrastructure.http.exceptions import BackendAuthError
from app.middlewares.session import restore_session
from app.modules.auth import BotAuthService
from app.modules.start.keyboards import (
    CREATE_CHARACTER_TEXT,
    HELP_TEXT,
    MY_CHARACTERS_TEXT,
    OPEN_MINI_APP_TEXT,
    main_menu_keyboard,
)
from app.modules.start.schemas.user import UserIdentity
from app.modules.start.service import StartService
from app.presentation.messages import AUTH_UNAVAILABLE_TEXT


async def handle_start(
    message: Message,
    start_service: StartService,
    auth_service: BotAuthService,
    state: FSMContext,
    config: BotConfig | None = None,
) -> None:
    user = UserIdentity.from_aiogram(message.from_user)

    if user.id > 0:
        try:
            await restore_session(state, auth_service, user.id, refresh=True)
        except BackendAuthError:
            await message.answer(AUTH_UNAVAILABLE_TEXT)
            return

    await message.answer(
        start_service.create_greeting(user),
        reply_markup=main_menu_keyboard(),
    )


async def handle_menu_create(message: Message, state, creation_service) -> None:
    from app.modules.character.router import handle_create

    await handle_create(message, state, creation_service)


async def handle_menu_characters(message: Message, state, management_service) -> None:
    from app.modules.character.management import handle_my_characters

    await handle_my_characters(message, state, management_service)


async def handle_menu_help(message: Message, config: BotConfig) -> None:
    from app.modules.start.mini_app import handle_help

    await handle_help(message, config)


async def handle_menu_app(message: Message, config: BotConfig) -> None:
    from app.modules.start.mini_app import handle_app

    await handle_app(message, config)


async def handle_main_menu_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer("Use the persistent menu below.", reply_markup=main_menu_keyboard())


def build_start_router() -> Router:
    router = Router(name="start")
    router.message.register(handle_start, CommandStart())
    router.message.register(handle_menu_create, F.text == CREATE_CHARACTER_TEXT)
    router.message.register(handle_menu_characters, F.text == MY_CHARACTERS_TEXT)
    router.message.register(handle_menu_app, F.text == OPEN_MINI_APP_TEXT)
    router.message.register(handle_menu_help, F.text == HELP_TEXT)
    router.callback_query.register(handle_main_menu_callback, F.data == "menu:main")
    return router


start_router = build_start_router()

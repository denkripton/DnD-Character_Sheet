from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.modules.auth import BotAuthService
from app.modules.start.schemas.user import UserIdentity
from app.modules.start.service import StartService
from app.utils.constants import AUTH_UNAVAILABLE_TEXT
from app.utils.exceptions import BackendAuthError


async def handle_start(
    message: Message,
    start_service: StartService,
    auth_service: BotAuthService,
    state: FSMContext,
) -> None:
    user = UserIdentity.from_aiogram(message.from_user)

    if user.id > 0:
        try:
            auth_context = await auth_service.authenticate(user.id)
        except BackendAuthError:
            await message.answer(AUTH_UNAVAILABLE_TEXT)
            return
        await state.update_data(auth=auth_context.model_dump())

    await message.answer(start_service.create_greeting(user))


def build_start_router() -> Router:
    router = Router(name="start")
    router.message.register(handle_start, CommandStart())
    return router


start_router = build_start_router()
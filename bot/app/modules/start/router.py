from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.modules.start.schemas.user import UserIdentity
from app.modules.start.service import StartService


async def handle_start(message: Message, start_service: StartService) -> None:
    user = UserIdentity.from_aiogram(message.from_user)
    await message.answer(start_service.create_greeting(user))


def build_start_router() -> Router:
    router = Router(name="start")
    router.message.register(handle_start, CommandStart())
    return router


start_router = build_start_router()
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage

from app.config import BotConfig
from app.infrastructure.fsm.storage import create_fsm_storage
from app.infrastructure.http.client import BackendApiClient
from app.middlewares.logging import LoggingMiddleware
from app.middlewares.session import SessionMiddleware
from app.modules.auth import BotAuthService
from app.modules.backstory.router import build_backstory_router
from app.modules.character import build_character_creation_router
from app.modules.character.management import build_management_router
from app.modules.start.mini_app import build_mini_app_router
from app.modules.start.router import build_start_router
from app.modules.start.service import StartService


def create_bot(config: BotConfig) -> Bot:
    return Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(
    config: BotConfig,
    storage: BaseStorage | None = None,
) -> Dispatcher:
    dispatcher = Dispatcher(storage=storage or create_fsm_storage(config))
    dispatcher.update.outer_middleware(LoggingMiddleware())
    dispatcher.message.outer_middleware(SessionMiddleware())
    dispatcher.callback_query.outer_middleware(SessionMiddleware())
    dispatcher.include_router(build_start_router())
    dispatcher.include_router(build_mini_app_router())
    dispatcher.include_router(build_backstory_router())
    dispatcher.include_router(build_character_creation_router())
    dispatcher.include_router(build_management_router())
    dispatcher["config"] = config
    dispatcher["start_service"] = StartService()
    dispatcher["auth_service"] = BotAuthService(BackendApiClient(config))
    return dispatcher

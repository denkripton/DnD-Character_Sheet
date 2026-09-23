from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage

from app.config import BotConfig
from app.infrastructure.fsm.storage import create_fsm_storage
from app.middlewares.logging import LoggingMiddleware
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
    dispatcher.include_router(build_start_router())
    dispatcher["config"] = config
    dispatcher["start_service"] = StartService()
    return dispatcher
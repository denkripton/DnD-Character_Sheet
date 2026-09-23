import asyncio
import inspect

import structlog
from aiogram.fsm.storage.base import BaseStorage

from app.api import create_bot, create_dispatcher
from app.config import load_config
from app.dependencies import build_rabbitmq_client
from app.utils.logging import configure_logging


async def close_storage(storage: BaseStorage) -> None:
    result = storage.close()
    if inspect.isawaitable(result):
        await result


async def main() -> None:
    config = load_config()
    configure_logging(config.LOG_LEVEL)
    logger = structlog.get_logger("app.main")

    bot = create_bot(config)
    dispatcher = create_dispatcher(config)
    rabbit = build_rabbitmq_client(config)
    dispatcher["rabbit"] = rabbit

    await rabbit.start()
    logger.info("bot_started")
    try:
        await dispatcher.start_polling(bot, close_bot_session=True)
    finally:
        await rabbit.close()
        await close_storage(dispatcher.storage)
        logger.info("bot_stopped")


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
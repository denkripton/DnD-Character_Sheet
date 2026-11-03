from aiogram import Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonCommands,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from app.config import BotConfig

MINI_APP_COMMANDS = (
    ("start", "Main menu"),
    ("app", "Open Mini App"),
    ("characters", "My characters"),
    ("create", "Create character"),
    ("backstory", "Generate backstory"),
    ("help", "Help"),
)


def build_mini_app_url(config: BotConfig, path: str = "") -> str | None:
    if not config.MINI_APP_URL:
        return None
    if not path:
        return config.MINI_APP_URL
    return f"{config.MINI_APP_URL.rstrip('/')}/{path.lstrip('/')}"


async def configure_bot_menu(bot, config: BotConfig) -> None:
    from aiogram.types import BotCommand

    await bot.set_my_commands(
        [
            BotCommand(command=name, description=description)
            for name, description in MINI_APP_COMMANDS
        ]
    )
    if config.MINI_APP_URL and config.MINI_APP_URL.startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Open app", web_app=WebAppInfo(url=config.MINI_APP_URL)
            )
        )
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def _send_app(message: Message, config: BotConfig, path: str = "") -> None:
    url = build_mini_app_url(config, path)
    if not url:
        await message.answer("The Mini App is not configured yet.")
        return
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Please open the Mini App in a private chat with this bot.")
        return
    if not url.startswith("https://"):
        await message.answer(
            f"The Mini App is available locally at {url}. Telegram Web App buttons require HTTPS."
        )
        return
    await message.answer(
        "Open your D&D character sheet:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Open Mini App", web_app=WebAppInfo(url=url))]
            ]
        ),
    )


async def handle_app(message: Message, config: BotConfig) -> None:
    await _send_app(message, config)


async def handle_characters(message: Message, config: BotConfig) -> None:
    await _send_app(message, config, "characters")


async def handle_help(message: Message, config: BotConfig) -> None:
    text = "Commands: /start, /app, /characters, /create, /backstory."
    if config.MINI_APP_URL:
        text += " Use /app to open the Mini App."
    await message.answer(text)


def build_mini_app_router() -> Router:
    router = Router(name="mini_app")
    router.message.register(handle_app, Command("app"))
    router.message.register(handle_characters, Command("characters"))
    router.message.register(handle_help, Command("help"))
    return router

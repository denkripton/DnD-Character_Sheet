import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.enums import ChatType
from aiogram.types import MenuButtonCommands

from app.config import BotConfig
from app.modules.start.mini_app import (
    MINI_APP_COMMANDS,
    configure_bot_menu,
    handle_app,
    handle_characters,
)


def test_menu_configuration_sets_commands_and_web_app_button():
    bot = AsyncMock()
    config = BotConfig(
        BOT_TOKEN="12345:test-token", MINI_APP_URL="https://app.example.com"
    )

    asyncio.run(configure_bot_menu(bot, config))

    assert [command.command for command in bot.set_my_commands.await_args.args[0]] == [
        command for command, _ in MINI_APP_COMMANDS
    ]
    assert bot.set_chat_menu_button.await_args.kwargs["menu_button"].web_app.url == config.MINI_APP_URL


def test_menu_configuration_without_url_skips_web_app_menu_button():
    bot = AsyncMock()
    asyncio.run(configure_bot_menu(bot, BotConfig(BOT_TOKEN="12345:test-token")))

    bot.set_my_commands.assert_awaited_once()
    assert isinstance(
        bot.set_chat_menu_button.await_args.kwargs["menu_button"],
        MenuButtonCommands,
    )


def test_http_development_url_keeps_telegram_commands_menu():
    bot = AsyncMock()
    config = BotConfig(
        BOT_TOKEN="12345:test-token", MINI_APP_URL="http://localhost:5173"
    )

    asyncio.run(configure_bot_menu(bot, config))

    assert isinstance(
        bot.set_chat_menu_button.await_args.kwargs["menu_button"], MenuButtonCommands
    )


def test_app_command_sends_private_web_app_button():
    message = AsyncMock()
    message.chat = SimpleNamespace(type=ChatType.PRIVATE)
    config = BotConfig(
        BOT_TOKEN="12345:test-token", MINI_APP_URL="https://app.example.com"
    )

    asyncio.run(handle_app(message, config))

    markup = message.answer.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].web_app.url == config.MINI_APP_URL


def test_characters_command_opens_characters_route():
    message = AsyncMock()
    message.chat = SimpleNamespace(type=ChatType.PRIVATE)
    config = BotConfig(
        BOT_TOKEN="12345:test-token", MINI_APP_URL="https://app.example.com/"
    )

    asyncio.run(handle_characters(message, config))

    markup = message.answer.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].web_app.url == "https://app.example.com/characters"


def test_app_command_handles_missing_url():
    message = AsyncMock()
    asyncio.run(handle_app(message, BotConfig(BOT_TOKEN="12345:test-token")))
    message.answer.assert_awaited_once_with("The Mini App is not configured yet.")


def test_http_development_url_is_not_sent_as_web_app_button():
    message = AsyncMock()
    message.chat = SimpleNamespace(type=ChatType.PRIVATE)
    config = BotConfig(
        BOT_TOKEN="12345:test-token", MINI_APP_URL="http://localhost:5173"
    )

    asyncio.run(handle_app(message, config))

    message.answer.assert_awaited_once_with(
        "The Mini App is available locally at http://localhost:5173. Telegram Web App buttons require HTTPS."
    )

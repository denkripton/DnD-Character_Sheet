from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from app.config import BotConfig
from app.modules.start.mini_app import build_mini_app_url, is_telegram_web_app_url

CREATE_CHARACTER_TEXT = "Create Character"
MY_CHARACTERS_TEXT = "My Characters"
OPEN_MINI_APP_TEXT = "Open Mini App"
HELP_TEXT = "Help"


def main_menu_keyboard(config: BotConfig | None = None) -> ReplyKeyboardMarkup:
    app_url = build_mini_app_url(config) if config else None
    characters_url = build_mini_app_url(config, "characters") if config else None
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=CREATE_CHARACTER_TEXT),
                KeyboardButton(
                    text=MY_CHARACTERS_TEXT,
                    web_app=WebAppInfo(url=characters_url)
                    if is_telegram_web_app_url(characters_url)
                    else None,
                ),
            ],
            [
                KeyboardButton(
                    text=OPEN_MINI_APP_TEXT,
                    web_app=WebAppInfo(url=app_url)
                    if is_telegram_web_app_url(app_url)
                    else None,
                ),
                KeyboardButton(text=HELP_TEXT),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

CREATE_CHARACTER_TEXT = "Create Character"
MY_CHARACTERS_TEXT = "My Characters"
OPEN_MINI_APP_TEXT = "Open Mini App"
HELP_TEXT = "Help"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CREATE_CHARACTER_TEXT), KeyboardButton(text=MY_CHARACTERS_TEXT)],
            [KeyboardButton(text=OPEN_MINI_APP_TEXT), KeyboardButton(text=HELP_TEXT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

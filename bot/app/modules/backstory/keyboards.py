from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CALLBACK_PREFIX = "bs"
CALLBACK_START = f"{CALLBACK_PREFIX}:start"
CALLBACK_GENERATE = f"{CALLBACK_PREFIX}:gen"
CALLBACK_ACCEPT = f"{CALLBACK_PREFIX}:accept"
CALLBACK_REGENERATE = f"{CALLBACK_PREFIX}:regen"
CALLBACK_EDIT = f"{CALLBACK_PREFIX}:edit"
CALLBACK_CANCEL = f"{CALLBACK_PREFIX}:cancel"
CALLBACK_CLOSE = f"{CALLBACK_PREFIX}:close"
CALLBACK_BACK = f"{CALLBACK_PREFIX}:back"


def backstory_hub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Generate backstory",
                    callback_data=CALLBACK_START,
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Done", callback_data=CALLBACK_CLOSE
                )
            ],
        ]
    )


def backstory_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎲 Generate", callback_data=CALLBACK_GENERATE
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Back", callback_data=CALLBACK_BACK
                ),
                InlineKeyboardButton(
                    text="❌ Cancel", callback_data=CALLBACK_CANCEL
                ),
            ],
        ]
    )


def backstory_review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Accept", callback_data=CALLBACK_ACCEPT
                ),
                InlineKeyboardButton(
                    text="🔄 Regenerate", callback_data=CALLBACK_REGENERATE
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Edit", callback_data=CALLBACK_EDIT
                ),
                InlineKeyboardButton(
                    text="❌ Cancel", callback_data=CALLBACK_CANCEL
                ),
            ],
        ]
    )


def backstory_edit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Back", callback_data=CALLBACK_BACK
                ),
                InlineKeyboardButton(
                    text="❌ Cancel", callback_data=CALLBACK_CANCEL
                ),
            ]
        ]
    )

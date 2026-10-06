from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.modules.character.steps import WizardStep

CALLBACK_PREFIX = "cc"
CALLBACK_SET = f"{CALLBACK_PREFIX}:set"
CALLBACK_GENERATE = f"{CALLBACK_PREFIX}:gen"
CALLBACK_MANUAL = f"{CALLBACK_PREFIX}:manual"
CALLBACK_BACK = f"{CALLBACK_PREFIX}:back"
CALLBACK_CANCEL = f"{CALLBACK_PREFIX}:cancel"


def navigation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Back", callback_data=CALLBACK_BACK),
                InlineKeyboardButton(text="❌ Cancel", callback_data=CALLBACK_CANCEL),
            ]
        ]
    )


def step_keyboard(step: WizardStep) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if step.options:
        rows.append(
            [
                InlineKeyboardButton(
                    text=option,
                    callback_data=f"{CALLBACK_SET}:{step.position}:{option}",
                )
                for option in step.options
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="✏️ Other / enter manually",
                    callback_data=f"{CALLBACK_MANUAL}:{step.position}",
                )
            ]
        )
    if step.generatable:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎲 Generate",
                    callback_data=f"{CALLBACK_GENERATE}:{step.position}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data=CALLBACK_BACK),
            InlineKeyboardButton(text="❌ Cancel", callback_data=CALLBACK_CANCEL),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)

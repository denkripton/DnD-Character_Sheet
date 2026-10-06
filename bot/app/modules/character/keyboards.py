from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.modules.character.steps import (
    STATS_GENERATOR_METHODS,
    STATS_METHODS,
    WizardStep,
)

CALLBACK_PREFIX = "cc"
CALLBACK_SET = f"{CALLBACK_PREFIX}:set"
CALLBACK_GENERATE = f"{CALLBACK_PREFIX}:gen"
CALLBACK_MANUAL = f"{CALLBACK_PREFIX}:manual"
CALLBACK_BACK = f"{CALLBACK_PREFIX}:back"
CALLBACK_CANCEL = f"{CALLBACK_PREFIX}:cancel"
CALLBACK_METHOD = f"{CALLBACK_PREFIX}:method"
CALLBACK_REGEN = f"{CALLBACK_PREFIX}:regen"
CALLBACK_EDIT = f"{CALLBACK_PREFIX}:edit"
CALLBACK_CONFIRM = f"{CALLBACK_PREFIX}:confirm"


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


def stats_method_keyboard() -> InlineKeyboardMarkup:
    labels = {
        "random": "🎲 Random (4d6)",
        "standard": "📋 Standard array",
        "point_buy": "🛒 Point buy",
        "manual": "✏️ Manual entry",
    }
    method_buttons = [
        InlineKeyboardButton(
            text=labels[method],
            callback_data=f"{CALLBACK_METHOD}:{method}",
        )
        for method in STATS_METHODS
    ]
    rows: list[list[InlineKeyboardButton]] = [
        method_buttons[:2],
        method_buttons[2:],
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data=CALLBACK_BACK),
            InlineKeyboardButton(text="❌ Cancel", callback_data=CALLBACK_CANCEL),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def stats_keyboard(method: str | None, has_stats: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if has_stats:
        if method in STATS_GENERATOR_METHODS:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="🎲 Regenerate",
                        callback_data=CALLBACK_REGEN,
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="✏️ Edit values",
                    callback_data=CALLBACK_EDIT,
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Confirm stats",
                    callback_data=CALLBACK_CONFIRM,
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

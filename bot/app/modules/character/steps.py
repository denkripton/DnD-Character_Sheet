from dataclasses import dataclass

from app.modules.character.states import CharacterCreationStates

POSITIONS = ("name", "race", "spec_class", "stats_method", "stats", "summary")

STATS_METHODS = ("random", "standard", "point_buy", "manual")
STATS_GENERATOR_METHODS = ("random", "standard", "point_buy")

STATS_METHOD_LABELS = {
    "random": "Random (4d6 drop lowest)",
    "standard": "Standard array",
    "point_buy": "Point buy",
    "manual": "Manual",
}

STATS_FIELDS = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)

STATS_ABBREVIATIONS = {
    "strength": "STR",
    "dexterity": "DEX",
    "constitution": "CON",
    "intelligence": "INT",
    "wisdom": "WIS",
    "charisma": "CHA",
}


@dataclass(frozen=True)
class WizardStep:
    position: str
    field: str
    prompt: str
    options: tuple[str, ...] = ()
    generatable: bool = True


STEPS: tuple[WizardStep, ...] = (
    WizardStep(
        position="name",
        field="name",
        prompt=(
            "Step {index}/{total} - Name\n"
            "Type the character's name in the chat or tap 🎲 Generate.\n"
            "/back - previous step, /cancel - abort"
        ),
    ),
    WizardStep(
        position="race",
        field="kind",
        prompt=(
            "Step {index}/{total} - Race / species\n"
            "Tap an option, type your own, or tap 🎲 Generate.\n"
            "/back - previous step, /cancel - abort"
        ),
        options=("Human", "Elf", "Dwarf"),
    ),
    WizardStep(
        position="spec_class",
        field="spec_class",
        prompt=(
            "Step {index}/{total} - Class\n"
            "Tap an option, type your own, or tap 🎲 Generate.\n"
            "/back - previous step, /cancel - abort"
        ),
        options=("Fighter", "Wizard", "Rogue"),
    ),
)


def stage_total() -> int:
    return len(POSITIONS) - 1


def position_index(position: str) -> int:
    return POSITIONS.index(position) + 1


def step_index(step: WizardStep) -> int:
    return position_index(step.position)


def prompt_for(step: WizardStep) -> str:
    return step.prompt.format(index=step_index(step), total=stage_total())


def stats_method_prompt() -> str:
    return (
        f"Step {position_index('stats_method')}/{stage_total()}"
        " - Stats generation method\n"
        "Choose how to assign ability scores:\n"
        "/back - previous step, /cancel - abort"
    )


def stats_entry_prompt() -> str:
    return (
        f"Step {position_index('stats')}/{stage_total()} - Ability scores\n"
        "Type six values in order (STR DEX CON INT WIS CHA),\n"
        "each from 8 to 15, spending exactly 27 points, for example:\n"
        "15 14 13 12 10 8\n"
        "/back - previous step, /cancel - abort"
    )


def stats_method_label(method: str | None) -> str:
    return STATS_METHOD_LABELS.get(method or "", "Manual")


def state_for_position(position: str):
    return getattr(CharacterCreationStates, position)


def position_for_state(state_value: str | None) -> str | None:
    if state_value is None:
        return None
    for position in POSITIONS:
        if state_for_position(position).state == state_value:
            return position
    return None


def step_for_position(position: str | None) -> WizardStep | None:
    if position is None:
        return None
    for step in STEPS:
        if step.position == position:
            return step
    return None


def previous_position(position: str) -> str | None:
    index = POSITIONS.index(position)
    if index <= 0:
        return None
    return POSITIONS[index - 1]


def next_position(position: str) -> str | None:
    index = POSITIONS.index(position)
    if index + 1 >= len(POSITIONS):
        return None
    return POSITIONS[index + 1]

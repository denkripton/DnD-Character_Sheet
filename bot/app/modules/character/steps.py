from dataclasses import dataclass

from app.modules.character.states import CharacterCreationStates

POSITIONS = ("name", "race", "spec_class", "summary")


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


def step_index(step: WizardStep) -> int:
    return STEPS.index(step) + 1


def prompt_for(step: WizardStep) -> str:
    return step.prompt.format(index=step_index(step), total=len(STEPS))


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

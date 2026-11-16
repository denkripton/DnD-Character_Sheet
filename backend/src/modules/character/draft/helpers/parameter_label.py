from src.modules.character.draft.constants import PARAMETER_LABELS


def parameter_label(parameter: str) -> str:
    return PARAMETER_LABELS.get(parameter, parameter)

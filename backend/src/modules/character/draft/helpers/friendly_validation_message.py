from pydantic import ValidationError
from src.modules.character.draft.helpers.parameter_label import parameter_label


def friendly_validation_message(exc: ValidationError) -> str:
    error = exc.errors()[0]
    location = error.get("loc") or ()
    field = str(location[0]) if location else ""
    label = parameter_label(field)
    error_type = error.get("type")
    if error_type == "string_too_long":
        max_length = error.get("ctx", {}).get("max_length")
        return f"{label} must be no more than {max_length} characters."
    if error_type == "extra_forbidden":
        return f"Unsupported parameter: {field}."
    if error_type == "string_type":
        return f"{label} must be a text value."
    if error_type == "missing":
        return f"{label} is required."
    return f"{label}: {error.get('msg', 'is invalid')}" + "."

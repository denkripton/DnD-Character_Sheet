from pydantic import ValidationError


def _stats_error_message(exc: ValidationError) -> str:
    error = exc.errors()[0]
    error_type = error.get("type")
    if error_type in ("greater_than_equal", "less_than_equal"):
        return "Each stat must be between 8 and 15."
    if error_type == "value_error":
        message = str(error.get("msg", ""))
        message = message.removeprefix("Value error, ")
        return message
    if error_type == "int_type":
        return "Stats must be whole numbers."
    if error_type == "missing":
        return "All six stats are required."
    return str(error.get("msg", "Stats are invalid."))

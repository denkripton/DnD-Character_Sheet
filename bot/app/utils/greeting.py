FALLBACK_NAME = "adventurer"


def greeting_text(name: str | None) -> str:
    resolved = name or FALLBACK_NAME
    return (
        f"Hello, {resolved}! I am your D&D character sheet assistant. "
        "Use /create_character to build a new character step by step."
    )
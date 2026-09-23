FALLBACK_NAME = "adventurer"


def greeting_text(name: str | None) -> str:
    resolved = name or FALLBACK_NAME
    return (
        f"Hello, {resolved}! I am your D&D character sheet assistant.\n"
        "Character management is coming soon — check back here."
    )
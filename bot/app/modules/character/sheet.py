from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

SHEET_SECTIONS = (
    ("overview", "Overview"),
    ("abilities", "Abilities"),
    ("combat", "Combat"),
    ("skills", "Skills"),
    ("features", "Features"),
    ("spells", "Spells"),
    ("inventory", "Inventory"),
    ("backstory", "Backstory"),
)
PAGE_SIZE = 18


def _value(value):
    return str(value) if value is not None and value != "" else "Not available"


def _modifier(value):
    if not isinstance(value, int) or isinstance(value, bool):
        return "?"
    return f"+{value}" if value >= 0 else str(value)


def _lines(character: dict, section: str) -> list[str]:
    if section == "overview":
        return [
            f"Name: {_value(character.get('name'))}", f"Race: {_value(character.get('kind'))}",
            f"Class: {_value(character.get('spec_class'))}", f"Subclass: {_value(character.get('subclass'))}",
            f"Level: {_value(character.get('level'))}", f"Background: {_value(character.get('background'))}",
            f"Alignment: {_value(character.get('alignment'))}",
            f"Experience points: {_value(character.get('experience_points'))}",
        ]
    if section == "abilities":
        stats, modifiers = character.get("stats") or {}, character.get("modifiers") or {}
        return [
            f"{label}: {_value(stats.get(field))} ({_modifier(modifiers.get(field))})"
            for field, label in (("strength", "STR"), ("dexterity", "DEX"), ("constitution", "CON"),
                                 ("intelligence", "INT"), ("wisdom", "WIS"), ("charisma", "CHA"))
        ]
    if section == "combat":
        combat = character.get("combat") or {}
        fields = (("current_hp", "Current HP"), ("max_hp", "Maximum HP"), ("temp_hp", "Temporary HP"),
                  ("armor_class", "Armor Class"), ("initiative", "Initiative"), ("speed", "Speed"),
                  ("hit_dice_total", "Hit Dice"), ("hit_dice_remaining", "Hit Dice remaining"),
                  ("proficiency_bonus", "Proficiency Bonus"))
        return [f"{label}: {_value(combat.get(field))}" for field, label in fields]
    if section == "skills":
        lines = []
        for ability, value in (character.get("saving_throws") or {}).items():
            proficient = value.get("proficient") if isinstance(value, dict) else value
            modifier = value.get("modifier") if isinstance(value, dict) else None
            suffix = f" ({_modifier(modifier)})" if modifier is not None else ""
            lines.append(f"Saving throw {ability.title()}: {'proficient' if proficient else 'not proficient'}{suffix}")
        for skill in character.get("skills") or []:
            status = "proficient" if skill.get("proficiency") else "not proficient"
            modifier = skill.get("modifier")
            suffix = f" ({_modifier(modifier)})" if modifier is not None else ""
            lines.append(f"{_value(skill.get('name'))} ({_value(skill.get('ability'))}): {status}{suffix}")
        return lines or ["No skills or saving throws are available."]
    if section == "features":
        lines = [f"{_value(item.get('name'))}: {_value(item.get('description'))}" for item in character.get("features") or []]
        lines.extend(f"{_value(item.get('category')).title()}: {_value(item.get('name'))}" for item in character.get("proficiencies") or [])
        return lines or ["No features or proficiencies are available."]
    if section == "spells":
        return ["Spellcasting data is not available for this character."]
    if section == "inventory":
        return ["Inventory data is not available for this character."]
    personality = character.get("personality") or {}
    backstory = (character.get("backstory") or {}).get("backstory")
    lines = ["No backstory has been saved for this character." if not backstory else f"Backstory: {_value(backstory)}"]
    for field, label in (("personality_traits", "Personality traits"), ("ideals", "Ideals"), ("bonds", "Bonds"), ("flaws", "Flaws")):
        if personality.get(field):
            lines.append(f"{label}: {_value(personality[field])}")
    return lines


def sheet_text(character: dict, section: str, page: int = 0) -> str:
    title = dict(SHEET_SECTIONS).get(section, "Overview")
    lines = _lines(character, section if section in dict(SHEET_SECTIONS) else "overview")
    pages = [lines[index:index + PAGE_SIZE] for index in range(0, len(lines), PAGE_SIZE)] or [[]]
    page = max(0, min(page, len(pages) - 1))
    return f"{_value(character.get('name'))} | {title}\n\n" + "\n".join(pages[page])


def sheet_page_count(character: dict, section: str) -> int:
    return max(1, (len(_lines(character, section)) + PAGE_SIZE - 1) // PAGE_SIZE)


def sheet_keyboard(character_id: str, section: str, page: int = 0, page_count: int = 1) -> InlineKeyboardMarkup:
    rows, buttons = [], []
    for key, label in SHEET_SECTIONS:
        buttons.append(InlineKeyboardButton(text=f"• {label}" if key == section else label, callback_data=f"cs:{character_id}:{key}:0"))
        if len(buttons) == 2:
            rows.append(buttons)
            buttons = []
    if buttons:
        rows.append(buttons)
    if page_count > 1:
        pagination = []
        if page > 0:
            pagination.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"cs:{character_id}:{section}:{page - 1}"))
        if page < page_count - 1:
            pagination.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"cs:{character_id}:{section}:{page + 1}"))
        rows.append(pagination)
    rows.extend([[InlineKeyboardButton(text="✏️ Edit Character", callback_data=f"cm:edit:{character_id}")],
                 [InlineKeyboardButton(text="⬅️ Back to Characters", callback_data="cm:back")]])
    return InlineKeyboardMarkup(inline_keyboard=rows)

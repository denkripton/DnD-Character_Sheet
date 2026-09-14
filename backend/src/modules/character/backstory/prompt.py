def build_backstory_prompt(character, context: dict) -> str:
    lines = [
        "Generate a relevant background story about this Dungeons & Dragons character.",
    ]

    core = []
    if character.name:
        core.append(f"Name: {character.name}")
    if character.kind:
        core.append(f"Race: {character.kind}")
    if character.spec_class:
        core.append(f"Class: {character.spec_class}")
    if character.background:
        core.append(f"Background: {character.background}")
    if character.alignment:
        core.append(f"Alignment: {character.alignment}")
    if character.level is not None:
        core.append(f"Level: {character.level}")

    lines.extend(core)

    personality = context.get("personality")
    if personality:
        values = [
            value
            for value in [
                getattr(personality, "personality_traits", ""),
                getattr(personality, "ideals", ""),
                getattr(personality, "bonds", ""),
                getattr(personality, "flaws", ""),
            ]
            if value
        ]
        if values:
            lines.append(f"Personality: {'; '.join(values)}")

    stats = context.get("stats")
    if stats:
        ability_scores = ", ".join(
            f"{flag.capitalize()} {value}"
            for flag in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
            if (value := getattr(stats, flag, None)) is not None
        )
        lines.append(f"Ability scores: {ability_scores}")

    combat = context.get("combat")
    if combat:
        details = []
        if combat.max_hp:
            details.append(f"HP {combat.max_hp}")
        if combat.armor_class:
            details.append(f"AC {combat.armor_class}")
        if combat.hit_dice_total:
            details.append(f"Hit dice {combat.hit_dice_total}")
        if details:
            lines.append(f"Combat: {', '.join(details)}")

    saving_throws = context.get("saving_throws")
    if saving_throws:
        proficient = [
            flag.capitalize()
            for flag in [
                "strength",
                "dexterity",
                "constitution",
                "intelligence",
                "wisdom",
                "charisma",
            ]
            if getattr(saving_throws, flag, False)
        ]
        if proficient:
            lines.append(f"Saving throw proficiencies: {', '.join(proficient)}")

    features = context.get("features") or []
    if features:
        rendered = []
        for feature in features:
            text = feature.name
            if getattr(feature, "description", ""):
                text = f"{text} - {feature.description}"
            rendered.append(text)
        lines.append(f"Features: {'; '.join(rendered)}")

    skills = context.get("skills") or []
    skilled = [
        skill.name for skill in skills if getattr(skill, "proficiency", False)
    ]
    if skilled:
        lines.append(f"Skill proficiencies: {', '.join(skilled)}")

    proficiencies = context.get("proficiencies") or []
    if proficiencies:
        lines.append(
            "Other proficiencies: "
            + "; ".join(
                f"{proficiency.category} {proficiency.name}"
                for proficiency in proficiencies
            )
        )

    lines.append(
        "Use this information about the character. Return a few sentences of "
        "backstory, about 500-700 symbols long. Return only the story text."
    )

    return "\n".join(lines)
def assign_stats(value_list):

    template_stats = {
        "strength": None,
        "dexterity": None,
        "constitution": None,
        "intelligence": None,
        "wisdom": None,
        "charisma": None,
    }

    for i, key in enumerate(template_stats.keys()):
        if i < len(value_list):
            template_stats[key] = value_list[i]
    return template_stats



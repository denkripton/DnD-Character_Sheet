def assign_stats(value_list):

    template_stats = {
    "Strength": None,
    "Dexterity": None,
    "Constitution": None,
    "Intelligence": None,
    "Wisdom": None,
    "Charisma": None
    }
    
    for i, k in enumerate(template_stats.keys()):
        if i < len(k):
            template_stats[k] = (value_list[i] - 10) // 2
    return template_stats
from src.modules.character.utils.hit_points.calculate_max_hit_points import (
    calculate_max_hit_points,
)
from src.modules.character.utils.hit_points.get_class_hit_die import get_class_hit_die
from src.modules.character.utils.hit_points.get_kind_hp_bonus import get_kind_hp_bonus
from src.modules.character.utils.hit_points.hit_dice_text import hit_dice_text
from src.modules.character.utils.hit_points.proficiency_bonus_for_level import (
    proficiency_bonus_for_level,
)


def recalculate_combat_hit_dice(combat, character, stats) -> None:
    die_size = get_class_hit_die(character.spec_class)
    constitution = getattr(stats, "constitution", None)
    con_mod = (constitution - 10) // 2 if isinstance(constitution, int) else 0

    extra_hp = get_kind_hp_bonus(character.kind)
    if getattr(combat, "bonus_hp", None) is not None:
        extra_hp += combat.bonus_hp

    combat.hit_dice_total = hit_dice_text(character.level, die_size)
    combat.max_hp = calculate_max_hit_points(
        character.level, die_size, con_mod, extra_hit_points=extra_hp
    )
    combat.proficiency_bonus = proficiency_bonus_for_level(character.level)
    combat.hit_dice_remaining = character.level

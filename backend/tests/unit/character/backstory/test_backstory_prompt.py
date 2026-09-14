import uuid

from src.modules.character.backstory.prompt import build_backstory_prompt
from src.modules.character.models import (
    Character,
    Combat,
    Feature,
    Personality,
    Proficiency,
    SavingThrows,
    Skill,
    Stat,
)


def _character():
    return Character(
        id=uuid.uuid4(),
        name="Grog",
        spec_class="Barbarian",
        kind="Human",
        alignment="Chaotic Good",
        background="Soldier",
        level=3,
        experience_points=0,
        owner_id="user-1",
    )


def _context():
    return {
        "stats": Stat(
            strength=16,
            dexterity=14,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=8,
        ),
        "combat": Combat(
            current_hp=30,
            max_hp=30,
            temp_hp=0,
            bonus_hp=0,
            armor_class=14,
            initiative=1,
            speed=30,
            proficiency_bonus=2,
            hit_dice_total="3d12",
            hit_dice_remaining=3,
            inspiration=False,
            death_save_successes=0,
            death_save_failures=0,
        ),
        "personality": Personality(
            personality_traits="Brave",
            ideals="Strength",
            bonds="Clan",
            flaws="Loud",
        ),
        "saving_throws": SavingThrows(strength=True, wisdom=True),
        "features": [Feature(name="Rage", description="Deals extra damage")],
        "skills": [Skill(name="Athletics", ability="strength", proficiency=True)],
        "proficiencies": [Proficiency(category="Armor", name="Shields")],
    }


def test_prompt_contains_core_character_info():
    prompt = build_backstory_prompt(_character(), _context())
    assert "Name: Grog" in prompt
    assert "Race: Human" in prompt
    assert "Class: Barbarian" in prompt
    assert "Background: Soldier" in prompt
    assert "Alignment: Chaotic Good" in prompt
    assert "Level: 3" in prompt


def test_prompt_contains_features_and_personality():
    prompt = build_backstory_prompt(_character(), _context())
    assert "Personality: Brave; Strength; Clan; Loud" in prompt
    assert "Rage - Deals extra damage" in prompt


def test_prompt_contains_stats_skills_and_proficiencies():
    prompt = build_backstory_prompt(_character(), _context())
    assert "Strength 16" in prompt
    assert "Athletics" in prompt
    assert "Saving throw proficiencies: Strength, Wisdom" in prompt
    assert "Armor Shields" in prompt


def test_prompt_asks_for_short_story():
    prompt = build_backstory_prompt(_character(), _context())
    assert "500-700" in prompt


def test_prompt_tolerates_empty_context():
    prompt = build_backstory_prompt(_character(), {})
    assert "Name: Grog" in prompt
    assert "Class: Barbarian" in prompt


def test_prompt_omits_saving_throws_when_none_proficient():
    context = _context()
    context["saving_throws"] = SavingThrows()
    prompt = build_backstory_prompt(_character(), context)
    assert "Saving throw proficiencies" not in prompt


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("backstory prompt tests passed")
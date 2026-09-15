from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import CombatRepository, StatsRepository
from src.modules.character.stats.schemas import StatsCreateSchema
from src.repositories.redis import cache
from src.modules.character.utils import (
    assign_stats,
    compute_modifiers,
    generate_point_buy_stats,
    generate_random_stats,
    generate_standard_array,
    recalculate_combat_hit_dice,
)


class StatsService:
    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        stats_repository: StatsRepository,
        combat_repository: CombatRepository,
    ):
        self.ownership = ownership_guard
        self.stats_repo = stats_repository
        self.combat_repo = combat_repository

    async def _save_stats(self, character, stats_dict: dict):
        existing_stats = await self.stats_repo.get_one(character_id=character.id)

        if existing_stats is not None:
            for key, value in stats_dict.items():
                setattr(existing_stats, key, value)
            stats = existing_stats
        else:
            stats = await self.stats_repo.create(**stats_dict, character_id=character.id)

        await self.stats_repo.session.commit()
        await self.stats_repo.session.refresh(stats)

        await cache.delete_pattern(f"stats:{character.id}")
        await self._recalculate_combat(character, stats)

        return stats

    async def _recalculate_combat(self, character, stats):
        combat = await self.combat_repo.get_one(character_id=character.id)
        if combat is not None:
            recalculate_combat_hit_dice(combat, character, stats)
            await self.combat_repo.session.commit()
            await self.combat_repo.session.refresh(combat)
            await cache.delete_pattern(f"combat:{character.id}")

    async def get_stats(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        key = f"stats:{character_id}"
        cached = await cache.get(key)
        if cached is not None:
            return cached

        stats = await self.stats_repo.get_one(character_id=character_id)
        if stats is None:
            result = {"stats": None, "modifiers": None}
            await cache.set(key, result)
            return result

        stats_dict = {
            "strength": stats.strength,
            "dexterity": stats.dexterity,
            "constitution": stats.constitution,
            "intelligence": stats.intelligence,
            "wisdom": stats.wisdom,
            "charisma": stats.charisma,
        }
        result = {"stats": stats_dict, "modifiers": compute_modifiers(stats_dict)}
        await cache.set(key, result)
        return result

    async def add_stats(self, user_id, character_id, data: StatsCreateSchema):
        character = await self.ownership.get_owned(user_id, character_id)

        value_list = [
            data.strength, data.dexterity, data.constitution,
            data.intelligence, data.wisdom, data.charisma,
        ]
        stats_dict = assign_stats(value_list=value_list)

        if data.background_increase is not None:
            for key, increment in data.background_increase.increases.items():
                stats_dict[key] += increment

        await self._save_stats(character, stats_dict)

        return {"stats": stats_dict, "modifiers": compute_modifiers(stats_dict)}

    async def generate_stats(self, user_id, character_id, method: str = "random"):
        character = await self.ownership.get_owned(user_id, character_id)

        if method == "standard":
            generated = generate_standard_array()
        elif method == "point_buy":
            generated = generate_point_buy_stats()
        else:
            generated = generate_random_stats()

        stats_dict = assign_stats(value_list=generated)
        await self._save_stats(character, stats_dict)

        return {"stats": stats_dict, "modifiers": compute_modifiers(stats_dict)}
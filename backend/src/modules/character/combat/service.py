from src.modules.character.combat.schemas import (
    CombatCreateSchema,
    CombatReadSchema,
)
from src.infrastructure.redis import cache
from src.utils.unit_of_work import UnitOfWork
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import CombatRepository, StatsRepository
from src.modules.character.utils.random_combat import generate_random_combat
from src.modules.character.utils.hit_points import (
    calculate_max_hit_points,
    get_class_hit_die,
    get_kind_hp_bonus,
    hit_dice_text,
    proficiency_bonus_for_level,
)


class CombatService:
    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        combat_repository: CombatRepository,
        stats_repository: StatsRepository,
        unit_of_work: UnitOfWork,
    ):
        self.ownership = ownership_guard
        self.repo = combat_repository
        self.stats_repo = stats_repository
        self.uow = unit_of_work

    async def _upsert(self, character_id, data: dict):
        obj = await self.repo.get_one(character_id=character_id)
        if obj is not None:
            for key, value in data.items():
                setattr(obj, key, value)
        else:
            obj = await self.repo.create(character_id=character_id, **data)

        await self.uow.commit()
        await self.uow.refresh(obj)
        await cache.delete_pattern(f"combat:{character_id}")
        return obj

    async def get_combat(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        key = f"combat:{character_id}"
        cached = await cache.get(key)
        if cached is not None:
            return CombatReadSchema(**cached)

        combat = await self.repo.get_one(character_id=character_id)
        result = (
            CombatReadSchema.model_validate(combat) if combat is not None else None
        )
        if result is not None:
            await cache.set(key, result.model_dump(mode="json"))
        return result

    async def generate_combat(self, user_id, character_id):
        payload = generate_random_combat()
        return await self.set_combat(
            user_id, character_id, CombatCreateSchema(**payload)
        )

    async def set_combat(self, user_id, character_id, data: CombatCreateSchema):
        character = await self.ownership.get_owned(user_id, character_id)
        stats = await self.stats_repo.get_one(character_id=character.id)

        payload = data.model_dump(mode="json", exclude_none=True)

        hit_die = get_class_hit_die(character.spec_class)
        constitution_modifier = 0
        if stats is not None:
            constitution_modifier = (stats.constitution - 10) // 2

        extra_hit_points = get_kind_hp_bonus(character.kind) + data.bonus_hp

        payload["hit_dice_total"] = hit_dice_text(character.level, hit_die)
        payload["max_hp"] = calculate_max_hit_points(
            character.level,
            hit_die,
            constitution_modifier,
            extra_hit_points=extra_hit_points,
        )
        payload["proficiency_bonus"] = proficiency_bonus_for_level(character.level)
        payload["hit_dice_remaining"] = character.level

        existing = await self.repo.get_one(character_id=character.id)
        if data.current_hp is not None:
            payload["current_hp"] = data.current_hp
        else:
            payload["current_hp"] = existing.max_hp if existing is not None else payload["max_hp"]

        return await self._upsert(character_id=character_id, data=payload)
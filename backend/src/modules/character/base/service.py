from src.config import settings
from src.utils.exceptions import RateLimitExceeded, ServiceError
from src.infrastructure.redis import cache
from src.utils.unit_of_work import UnitOfWork
from src.modules.auth.repository import UserRepository
from src.modules.character.base.enums.generation_limits import GenerationLimits
from src.modules.character.base.schemas import (
    CharacterCreateSchema,
    CharacterReadSchema,
    CharacterUpdateSchema,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import (
    CharacterRepository,
    CombatRepository,
    StatsRepository,
)
from src.modules.character.utils.hit_points import recalculate_combat_hit_dice
from src.modules.character.utils.random_character import generate_random_character
from src.utils.interfaces.rate_limiter import RateLimiter


class CharacterService:
    def __init__(
        self,
        character_repository: CharacterRepository,
        user_repository: UserRepository,
        ownership_guard: CharacterOwnershipGuard,
        combat_repository: CombatRepository,
        stats_repository: StatsRepository,
        unit_of_work: UnitOfWork,
        rate_limiter: RateLimiter,
    ):
        self.character_repo = character_repository
        self.user_repo = user_repository
        self.ownership = ownership_guard
        self.combat_repo = combat_repository
        self.stats_repo = stats_repository
        self.uow = unit_of_work
        self.rate_limiter = rate_limiter

    async def _enforce_creation_limit(self, user_id: str) -> None:
        result = await self.rate_limiter.is_limited(
            user_id=user_id,
            category=GenerationLimits.KEY_PREFIX.value,
            max_requests=settings.CHARACTER_GENERATION_DAILY_LIMIT,
            time_window=GenerationLimits.DAILY_WINDOW_SECONDS.value,
        )
        if not result.allowed:
            raise RateLimitExceeded(
                limit=result.max_allowed,
                used=result.current_usage,
                retry_after=result.retry_after,
            )

    async def character_creation(self, user_id, data: CharacterCreateSchema):
        await self._enforce_creation_limit(user_id)

        data = data.model_dump()

        existing_user = await self.user_repo.get_by_id(user_id)
        if existing_user is None:
            raise ServiceError(code=422, msg="User does not exist")

        data["owner_id"] = user_id

        character = await self.character_repo.create(**data)
        await self.uow.commit()
        await self.uow.refresh(character)

        await cache.delete_pattern(f"characters:list:{user_id}*")

        return CharacterReadSchema.model_validate(character)

    async def generate_character(self, user_id):
        payload = generate_random_character()
        return await self.character_creation(
            user_id, CharacterCreateSchema(**payload)
        )

    async def update_character(self, user_id, character_id, data: CharacterUpdateSchema):
        character = await self.ownership.get_owned(user_id, character_id)
        update = data.model_dump(exclude_none=True)

        if not update:
            raise ServiceError(code=422, msg="Nothing to update")

        for key, value in update.items():
            setattr(character, key, value)

        if "level" in update or "spec_class" in update or "kind" in update:
            await self._recalculate_combat(character)

        await self.uow.commit()
        await self.uow.refresh(character)

        await cache.delete_pattern(f"characters:by_id:{character_id}")
        await cache.delete_pattern(f"characters:list:{user_id}*")

        return CharacterReadSchema.model_validate(character)

    async def _recalculate_combat(self, character):
        combat = await self.combat_repo.get_one(character_id=character.id)
        if combat is None:
            return
        stats = await self.stats_repo.get_one(character_id=character.id)
        recalculate_combat_hit_dice(combat, character, stats)
        await cache.delete_pattern(f"combat:{character.id}")

    async def get_all_characters(self, user_id):
        key = f"characters:list:{user_id}"
        cached = await cache.get(key)
        if cached is not None:
            return [CharacterReadSchema(**c) for c in cached]

        characters = await self.character_repo.get_many(owner_id=user_id)
        result = [CharacterReadSchema.model_validate(char) for char in characters]
        await cache.set(key, [c.model_dump(mode="json") for c in result])
        return result

    async def get_character_by_id(self, character_id):
        key = f"characters:by_id:{character_id}"
        cached = await cache.get(key)
        if cached is not None:
            return CharacterReadSchema(**cached)

        character = await self.character_repo.get_by_id(character_id)
        if character is None:
            raise ServiceError(code=422, msg="Character does not exist")

        result = CharacterReadSchema.model_validate(character)
        await cache.set(key, result.model_dump(mode="json"))
        return result

    async def delete_character(self, user_id, character_id):
        character = await self.ownership.get_owned(user_id, character_id)

        await self.character_repo.delete_obj(character.id)
        await self.uow.commit()

        await cache.delete_pattern(f"*:{character_id}")
        await cache.delete_pattern(f"characters:list:{user_id}*")

        return {"message": "Character has been deleted"}
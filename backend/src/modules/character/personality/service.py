from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.personality.schemas import (
    PersonalityCreateSchema,
    PersonalityReadSchema,
)
from src.modules.character.repositories import PersonalityRepository
from src.infrastructure.redis import cache
from src.utils.unit_of_work import UnitOfWork
from src.modules.character.utils.random_personality import generate_random_personality


class PersonalityService:
    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        personality_repository: PersonalityRepository,
        unit_of_work: UnitOfWork,
    ):
        self.ownership = ownership_guard
        self.repo = personality_repository
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
        await cache.delete_pattern(f"personality:{character_id}")
        return obj

    async def get_personality(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        key = f"personality:{character_id}"
        cached = await cache.get(key)
        if cached is not None:
            return PersonalityReadSchema(**cached)

        personality = await self.repo.get_one(character_id=character_id)
        result = (
            PersonalityReadSchema.model_validate(personality)
            if personality is not None
            else None
        )
        if result is not None:
            await cache.set(key, result.model_dump(mode="json"))
        return result

    async def generate_personality(self, user_id, character_id):
        payload = generate_random_personality()
        return await self.set_personality(
            user_id, character_id, PersonalityCreateSchema(**payload)
        )

    async def set_personality(self, user_id, character_id, data: PersonalityCreateSchema):
        await self.ownership.get_owned(user_id, character_id)
        return await self._upsert(
            character_id=character_id,
            data=data.model_dump(mode="json"),
        )
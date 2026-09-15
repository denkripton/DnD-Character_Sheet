from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import SavingThrowsRepository
from src.modules.character.saving_throws.schemas import (
    SavingThrowsCreateSchema,
    SavingThrowsReadSchema,
)
from src.repositories.redis import cache
from src.modules.character.utils.random_saving_throws import (
    generate_random_saving_throws,
)


class SavingThrowsService:
    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        saving_throws_repository: SavingThrowsRepository,
    ):
        self.ownership = ownership_guard
        self.repo = saving_throws_repository

    async def _upsert(self, character_id, data: dict):
        obj = await self.repo.get_one(character_id=character_id)
        if obj is not None:
            for key, value in data.items():
                setattr(obj, key, value)
        else:
            obj = await self.repo.create(character_id=character_id, **data)

        await self.repo.session.commit()
        await self.repo.session.refresh(obj)
        await cache.delete_pattern(f"saving_throws:{character_id}")
        return obj

    async def get_saving_throws(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        key = f"saving_throws:{character_id}"
        cached = await cache.get(key)
        if cached is not None:
            return SavingThrowsReadSchema(**cached)

        values = await self.repo.get_one(character_id=character_id)
        result = (
            SavingThrowsReadSchema.model_validate(values) if values is not None else None
        )
        if result is not None:
            await cache.set(key, result.model_dump(mode="json"))
        return result

    async def generate_saving_throws(self, user_id, character_id):
        payload = generate_random_saving_throws()
        return await self.set_saving_throws(
            user_id, character_id, SavingThrowsCreateSchema(**payload)
        )

    async def set_saving_throws(self, user_id, character_id, data: SavingThrowsCreateSchema):
        await self.ownership.get_owned(user_id, character_id)
        return await self._upsert(
            character_id=character_id,
            data=data.model_dump(mode="json"),
        )
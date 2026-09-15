from src.exceptions import ServiceError
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.proficiencies.schemas import (
    ProficiencyCreateSchema,
    ProficiencyReadSchema,
)
from src.repositories.redis import cache
from src.modules.character.repositories import ProficiencyRepository
from src.modules.character.utils.random_proficiencies import generate_random_proficiencies


class ProficiencyService:
    item_name = "proficiency"

    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        proficiency_repository: ProficiencyRepository,
    ):
        self.ownership = ownership_guard
        self.repo = proficiency_repository

    async def generate_proficiencies(self, user_id, character_id, count: int | None = None):
        character = await self.ownership.get_owned(user_id, character_id)
        existing = {
            prof.name for prof in await self.repo.get_many(character_id=character.id)
        }

        created = []
        for item in generate_random_proficiencies(count, exclude=existing):
            obj = await self.repo.create(**item, character_id=character.id)
            created.append(obj)

        await self.repo.session.commit()
        for obj in created:
            await self.repo.session.refresh(obj)
        await cache.delete_pattern(f"proficiencies:{character.id}")
        return created

    async def get_proficiencies(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        key = f"proficiencies:{character_id}"
        cached = await cache.get(key)
        if cached is not None:
            return [ProficiencyReadSchema(**c) for c in cached]

        proficiencies = await self.repo.get_many(character_id=character_id)
        result = [ProficiencyReadSchema.model_validate(p) for p in proficiencies]
        await cache.set(key, [p.model_dump(mode="json") for p in result])
        return result

    async def add_proficiency(self, user_id, character_id, data: ProficiencyCreateSchema):
        character = await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.create(
            **data.model_dump(mode="json"), character_id=character.id
        )

        await self.repo.session.commit()
        await self.repo.session.refresh(obj)
        await cache.delete_pattern(f"proficiencies:{character.id}")
        return obj

    async def update_proficiency(
        self, user_id, character_id, proficiency_id, data: ProficiencyCreateSchema
    ):
        await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.get_one(id=proficiency_id, character_id=character_id)
        if obj is None:
            raise ServiceError(
                code=422, msg=f"{self.item_name.capitalize()} does not exist"
            )

        for key, value in data.model_dump(mode="json").items():
            setattr(obj, key, value)

        await self.repo.session.commit()
        await self.repo.session.refresh(obj)
        await cache.delete_pattern(f"proficiencies:{character_id}")
        return obj

    async def delete_proficiency(self, user_id, character_id, proficiency_id):
        await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.get_one(id=proficiency_id, character_id=character_id)
        if obj is None:
            raise ServiceError(
                code=422, msg=f"{self.item_name.capitalize()} does not exist"
            )

        await self.repo.delete_obj(obj.id)
        await self.repo.session.commit()
        await cache.delete_pattern(f"proficiencies:{character_id}")
        return {"message": f"{self.item_name.capitalize()} has been deleted"}
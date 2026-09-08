from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.personality.schemas import PersonalityCreateSchema
from src.modules.character.repositories import PersonalityRepository


class PersonalityService:
    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        personality_repository: PersonalityRepository,
    ):
        self.ownership = ownership_guard
        self.repo = personality_repository

    async def _upsert(self, character_id, data: dict):
        obj = await self.repo.get_one(character_id=character_id)
        if obj is not None:
            for key, value in data.items():
                setattr(obj, key, value)
        else:
            obj = await self.repo.create(character_id=character_id, **data)

        await self.repo.session.commit()
        await self.repo.session.refresh(obj)
        return obj

    async def get_personality(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        return await self.repo.get_one(character_id=character_id)

    async def set_personality(self, user_id, character_id, data: PersonalityCreateSchema):
        await self.ownership.get_owned(user_id, character_id)
        return await self._upsert(
            character_id=character_id,
            data=data.model_dump(mode="json"),
        )
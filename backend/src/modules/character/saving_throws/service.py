from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import SavingThrowsRepository
from src.modules.character.saving_throws.schemas import SavingThrowsCreateSchema


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
        return obj

    async def get_saving_throws(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        return await self.repo.get_one(character_id=character_id)

    async def set_saving_throws(self, user_id, character_id, data: SavingThrowsCreateSchema):
        await self.ownership.get_owned(user_id, character_id)
        return await self._upsert(
            character_id=character_id,
            data=data.model_dump(mode="json"),
        )
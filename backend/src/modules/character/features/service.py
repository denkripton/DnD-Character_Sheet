from src.exceptions import ServiceError
from src.modules.character.features.schemas import FeatureCreateSchema
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import FeatureRepository


class FeatureService:
    item_name = "feature"

    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        feature_repository: FeatureRepository,
    ):
        self.ownership = ownership_guard
        self.repo = feature_repository

    async def get_features(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        return await self.repo.get_many(character_id=character_id)

    async def add_feature(self, user_id, character_id, data: FeatureCreateSchema):
        character = await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.create(
            **data.model_dump(mode="json"), character_id=character.id
        )

        await self.repo.session.commit()
        await self.repo.session.refresh(obj)
        return obj

    async def update_feature(self, user_id, character_id, feature_id, data: FeatureCreateSchema):
        await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.get_one(id=feature_id, character_id=character_id)
        if obj is None:
            raise ServiceError(
                code=422, msg=f"{self.item_name.capitalize()} does not exist"
            )

        for key, value in data.model_dump(mode="json").items():
            setattr(obj, key, value)

        await self.repo.session.commit()
        await self.repo.session.refresh(obj)
        return obj

    async def delete_feature(self, user_id, character_id, feature_id):
        await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.get_one(id=feature_id, character_id=character_id)
        if obj is None:
            raise ServiceError(
                code=422, msg=f"{self.item_name.capitalize()} does not exist"
            )

        await self.repo.delete_obj(obj.id)
        await self.repo.session.commit()
        return {"message": f"{self.item_name.capitalize()} has been deleted"}
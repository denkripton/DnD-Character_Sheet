from src.exceptions import ServiceError
from src.modules.character.features.schemas import (
    FeatureCreateSchema,
    FeatureReadSchema,
)
from src.infrastructure.redis import cache
from src.utils.unit_of_work import UnitOfWork
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import FeatureRepository
from src.modules.character.utils.random_features import generate_random_features


class FeatureService:
    item_name = "feature"

    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        feature_repository: FeatureRepository,
        unit_of_work: UnitOfWork,
    ):
        self.ownership = ownership_guard
        self.repo = feature_repository
        self.uow = unit_of_work

    async def generate_features(self, user_id, character_id, count: int | None = None):
        character = await self.ownership.get_owned(user_id, character_id)
        existing = {
            feature.name
            for feature in await self.repo.get_many(character_id=character.id)
        }

        created = []
        for item in generate_random_features(count, exclude=existing):
            obj = await self.repo.create(**item, character_id=character.id)
            created.append(obj)

        await self.uow.commit()
        for obj in created:
            await self.uow.refresh(obj)
        await cache.delete_pattern(f"features:{character.id}")
        return created

    async def get_features(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        key = f"features:{character_id}"
        cached = await cache.get(key)
        if cached is not None:
            return [FeatureReadSchema(**c) for c in cached]

        features = await self.repo.get_many(character_id=character_id)
        result = [FeatureReadSchema.model_validate(f) for f in features]
        await cache.set(key, [f.model_dump(mode="json") for f in result])
        return result

    async def add_feature(self, user_id, character_id, data: FeatureCreateSchema):
        character = await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.create(
            **data.model_dump(mode="json"), character_id=character.id
        )

        await self.uow.commit()
        await self.uow.refresh(obj)
        await cache.delete_pattern(f"features:{character.id}")
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

        await self.uow.commit()
        await self.uow.refresh(obj)
        await cache.delete_pattern(f"features:{character_id}")
        return obj

    async def delete_feature(self, user_id, character_id, feature_id):
        await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.get_one(id=feature_id, character_id=character_id)
        if obj is None:
            raise ServiceError(
                code=422, msg=f"{self.item_name.capitalize()} does not exist"
            )

        await self.repo.delete_obj(obj.id)
        await self.uow.commit()
        await cache.delete_pattern(f"features:{character_id}")
        return {"message": f"{self.item_name.capitalize()} has been deleted"}
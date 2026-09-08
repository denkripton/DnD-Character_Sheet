from src.exceptions import ServiceError
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import SkillRepository
from src.modules.character.skills.schemas import SkillCreateSchema
from src.modules.character.utils.random_skills import generate_random_skills


class SkillService:
    item_name = "skill"

    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        skill_repository: SkillRepository,
    ):
        self.ownership = ownership_guard
        self.repo = skill_repository

    async def generate_skills(self, user_id, character_id, count: int | None = None):
        character = await self.ownership.get_owned(user_id, character_id)
        existing = {skill.name for skill in await self.repo.get_many(character_id=character.id)}

        created = []
        for item in generate_random_skills(count, exclude=existing):
            obj = await self.repo.create(**item, character_id=character.id)
            created.append(obj)

        await self.repo.session.commit()
        for obj in created:
            await self.repo.session.refresh(obj)
        return created

    async def get_skills(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        return await self.repo.get_many(character_id=character_id)

    async def add_skill(self, user_id, character_id, data: SkillCreateSchema):
        character = await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.create(**data.model_dump(mode="json"), character_id=character.id)

        await self.repo.session.commit()
        await self.repo.session.refresh(obj)
        return obj

    async def update_skill(self, user_id, character_id, skill_id, data: SkillCreateSchema):
        await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.get_one(id=skill_id, character_id=character_id)
        if obj is None:
            raise ServiceError(
                code=422, msg=f"{self.item_name.capitalize()} does not exist"
            )

        for key, value in data.model_dump(mode="json").items():
            setattr(obj, key, value)

        await self.repo.session.commit()
        await self.repo.session.refresh(obj)
        return obj

    async def delete_skill(self, user_id, character_id, skill_id):
        await self.ownership.get_owned(user_id, character_id)
        obj = await self.repo.get_one(id=skill_id, character_id=character_id)
        if obj is None:
            raise ServiceError(
                code=422, msg=f"{self.item_name.capitalize()} does not exist"
            )

        await self.repo.delete_obj(obj.id)
        await self.repo.session.commit()
        return {"message": f"{self.item_name.capitalize()} has been deleted"}
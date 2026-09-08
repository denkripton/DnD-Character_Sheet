from src.exceptions import ServiceError
from src.modules.auth.repository import UserRepository
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


class CharacterService:
    def __init__(
        self,
        character_repository: CharacterRepository,
        user_repository: UserRepository,
        ownership_guard: CharacterOwnershipGuard,
        combat_repository: CombatRepository,
        stats_repository: StatsRepository,
    ):
        self.character_repo = character_repository
        self.user_repo = user_repository
        self.ownership = ownership_guard
        self.combat_repo = combat_repository
        self.stats_repo = stats_repository

    async def character_creation(self, user_id, data: CharacterCreateSchema):
        data = data.model_dump()

        existing_user = await self.user_repo.get_by_id(user_id)
        if existing_user is None:
            raise ServiceError(code=422, msg="User does not exist")

        data["owner_id"] = user_id

        character = await self.character_repo.create(**data)
        await self.character_repo.session.commit()
        await self.character_repo.session.refresh(character)

        return CharacterReadSchema.model_validate(character)

    async def update_character(self, user_id, character_id, data: CharacterUpdateSchema):
        character = await self.ownership.get_owned(user_id, character_id)
        update = data.model_dump(exclude_none=True)

        if not update:
            raise ServiceError(code=422, msg="Nothing to update")

        for key, value in update.items():
            setattr(character, key, value)

        await self.character_repo.session.commit()
        await self.character_repo.session.refresh(character)

        if "level" in update or "spec_class" in update or "kind" in update:
            await self._recalculate_combat(character)

        return CharacterReadSchema.model_validate(character)

    async def _recalculate_combat(self, character):
        combat = await self.combat_repo.get_one(character_id=character.id)
        if combat is None:
            return
        stats = await self.stats_repo.get_one(character_id=character.id)
        recalculate_combat_hit_dice(combat, character, stats)
        await self.combat_repo.session.commit()
        await self.combat_repo.session.refresh(combat)

    async def get_all_characters(self, user_id):
        characters = await self.character_repo.get_many(owner_id=user_id)
        return [CharacterReadSchema.model_validate(char) for char in characters]

    async def get_character_by_id(self, character_id):
        character = await self.character_repo.get_by_id(character_id)
        if character is None:
            raise ServiceError(code=422, msg="Character does not exist")

        return CharacterReadSchema.model_validate(character)

    async def delete_character(self, user_id, character_id):
        character = await self.ownership.get_owned(user_id, character_id)

        await self.character_repo.delete_obj(character.id)
        await self.character_repo.session.commit()

        return {"message": "Character has been deleted"}
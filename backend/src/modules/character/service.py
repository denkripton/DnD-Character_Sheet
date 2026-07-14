from src.exceptions import ServiceError
from src.modules.auth.repository import UserRepository
from src.modules.character.repositories import CharacterRepository, StatsRepository
from src.modules.character.schemas import (
    CharacterCreateSchema,
    CharacterReadSchema,
    StatsCreateSchema,
)
from src.modules.character.utils import assign_stats, generate_random_stats, compute_modifiers


class CharacterService:
    def __init__(
        self,
        character_repository: CharacterRepository,
        user_repository: UserRepository,
        stats_repository: StatsRepository,
    ):
        self.character_repo = character_repository
        self.stats_repo = stats_repository
        self.user_repo = user_repository

    async def character_creation(self, user_id, data: CharacterCreateSchema):
        data = data.model_dump()

        existing_user = await self.user_repo.get_by_id(user_id)

        if existing_user is None:
            raise ServiceError(code=422, msg="User does not exist")

        data["owner_id"] = user_id

        character = await self.character_repo.create(**data)
        await self.character_repo.session.commit()
        await self.character_repo.session.refresh(character)

        char_dict = CharacterCreateSchema.model_validate(character).model_dump()
        char_dict["id"] = character.id

        return char_dict

    async def get_all_characters(self, user_id):
        characters = await self.character_repo.get_many(owner_id=user_id)

        return_list = []
        for char in characters:
            stats = await self.stats_repo.get_one(character_id=char.id)
            char_dict = CharacterCreateSchema.model_validate(char).model_dump()
            char_dict["id"] = char.id
            if stats is not None:
                stats_dict = {
                    "strength": stats.strength,
                    "dexterity": stats.dexterity,
                    "constitution": stats.constitution,
                    "intelligence": stats.intelligence,
                    "wisdom": stats.wisdom,
                    "charisma": stats.charisma,
                }
                char_dict["stats"] = stats_dict
                char_dict["modifiers"] = compute_modifiers(stats_dict)
            else:
                char_dict["stats"] = None
                char_dict["modifiers"] = None

            return_list.append(char_dict)
        return return_list

    async def get_character_by_id(self, character_id):

        character = await self.character_repo.get_by_id(character_id)

        if character is None:
            raise ServiceError(code=422, msg="Character does not exist")

        char_dict = CharacterCreateSchema.model_validate(character).model_dump()
        char_dict["id"] = character.id
        
        stats = await self.stats_repo.get_one(character_id=character.id)
        if stats is not None:
            stats_dict = {
                "strength": stats.strength,
                "dexterity": stats.dexterity,
                "constitution": stats.constitution,
                "intelligence": stats.intelligence,
                "wisdom": stats.wisdom,
                "charisma": stats.charisma,
            }
            char_dict["stats"] = stats_dict
            char_dict["modifiers"] = compute_modifiers(stats_dict)
        else:
            char_dict["stats"] = None
            char_dict["modifiers"] = None

        return char_dict

    async def delete_character(self, user_id, character_id):
        existing_user = await self.user_repo.get_by_id(user_id)

        if existing_user is None:
            raise ServiceError(code=422, msg="User does not exist")

        character = await self.character_repo.get_one(
            id=character_id, owner_id=existing_user.id
        )

        if character is None:
            raise ServiceError(code=422, msg="Character does not exist")

        await self.character_repo.delete_obj(character.id)
        await self.character_repo.session.commit()

        return {"message": "Character has been deleted"}

    async def generate_stats(self, user_id, character_id):
        existing_user = await self.user_repo.get_by_id(user_id)

        if existing_user is None:
            raise ServiceError(code=422, msg="User does not exist")

        character = await self.character_repo.get_one(
            id=character_id, owner_id=existing_user.id
        )

        if character is None:
            raise ServiceError(code=422, msg="Character does not exist")

        existing_stats = await self.stats_repo.get_one(character_id=character.id)

        random_stats = generate_random_stats()
        stats_dict = assign_stats(value_list=random_stats)

        if existing_stats is not None:
            for key, value in stats_dict.items():
                setattr(existing_stats, key, value)
            stats = existing_stats
        else:
            stats = await self.stats_repo.create(
                **stats_dict, character_id=character.id
            )

        await self.stats_repo.session.commit()
        await self.stats_repo.session.refresh(stats)

        return CharacterReadSchema(
            name=character.name,
            spec_class=character.spec_class,
            kind=character.kind,
            stats=stats_dict,
            modifiers=compute_modifiers(stats_dict),
            id=character.id,
        )

    async def add_stats(self, user_id, character_id, data: StatsCreateSchema):
        existing_user = await self.user_repo.get_by_id(user_id)

        if existing_user is None:
            raise ServiceError(code=422, msg="User does not exist")

        character = await self.character_repo.get_one(
            id=character_id, owner_id=existing_user.id
        )

        if character is None:
            raise ServiceError(code=422, msg="Character does not exist")

        existing_stats = await self.stats_repo.get_one(character_id=character.id)

        value_list = [
            data.strength, data.dexterity, data.constitution,
            data.intelligence, data.wisdom, data.charisma
        ]
        stats_dict = assign_stats(value_list=value_list)

        if existing_stats is not None:
            for key, value in stats_dict.items():
                setattr(existing_stats, key, value)
            stats = existing_stats
        else:
            stats = await self.stats_repo.create(
                **stats_dict, character_id=character.id
            )

        await self.stats_repo.session.commit()
        await self.stats_repo.session.refresh(stats)

        return CharacterReadSchema(
            name=character.name,
            spec_class=character.spec_class,
            kind=character.kind,
            stats=stats_dict,
            modifiers=compute_modifiers(stats_dict),
            id=character.id,
        )

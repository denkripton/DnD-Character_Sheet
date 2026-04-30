from src.exceptions import ServiceError

from src.modules.character.repositories.character import CharacterRepository
from src.modules.auth.repository import UserRepository

from src.modules.character.schemas import CharacterCreateSchema

class CharacterService:
    def __init__(self, character_repository: CharacterRepository, user_repository: UserRepository):
        self.character_repo = character_repository
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
        char_dict["creator"] = {"name": existing_user.username}

        return char_dict

    async def get_all_charaters(self, user_id):
        characters = await self.character_repo.get_many(owner_id=user_id)

        return_list = []
        for char in characters:
            char_dict = CharacterCreateSchema.model_validate(char).model_dump()
            return_list.append(char_dict)
        return return_list
from typing import Any

from src.exceptions import ServiceError
from src.modules.auth.repository import UserRepository
from src.modules.character.repositories import CharacterRepository


class CharacterOwnershipGuard:
    def __init__(
        self,
        character_repository: CharacterRepository,
        user_repository: UserRepository,
    ):
        self.character_repo = character_repository
        self.user_repo = user_repository

    async def get_owned(self, user_id: str, character_id: Any):
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise ServiceError(code=422, msg="User does not exist")

        character = await self.character_repo.get_one(
            id=character_id, owner_id=user.id
        )
        if character is None:
            raise ServiceError(code=422, msg="Character does not exist")

        return character
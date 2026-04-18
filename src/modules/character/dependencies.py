from typing import Optional

from fastapi import Depends

from src.modules.character.service import CharacterService
from src.modules.auth.repository import UserRepository
from src.modules.auth.dependencies import user_repository
from src.modules.character.repositories.character import CharacterRepository
from src.dependencies import RepoFactory
from src.modules.auth.utils import JWT


character_repository = RepoFactory(repo=CharacterRepository)


class CharacterServiceFactory:
    def __call__(
        self, 
        character_repo: CharacterRepository = Depends(character_repository),
        user_repo: UserRepository = Depends(user_repository),
        ):
        return CharacterService(user_repository=user_repo, character_repository=character_repo)

get_character_service = CharacterServiceFactory()

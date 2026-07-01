from fastapi import Depends
from src.dependencies import RepoFactory
from src.modules.auth.dependencies import user_repository
from src.modules.auth.repository import UserRepository
from src.modules.character.repositories.character import CharacterRepository
from src.modules.character.service import CharacterService

character_repository = RepoFactory(repo=CharacterRepository)


class CharacterServiceFactory:
    def __init__(self, service_cls: type[CharacterService] = CharacterService):
        self.service_cls = service_cls

    def create(
        self,
        character_repo: CharacterRepository = Depends(character_repository),
        user_repo: UserRepository = Depends(user_repository),
    ) -> CharacterService:
        return self.service_cls(
            character_repository=character_repo, user_repository=user_repo
        )


character_service_factory = CharacterServiceFactory()


def get_character_service(
    character_repo: CharacterRepository = Depends(character_repository),
    user_repo: UserRepository = Depends(user_repository),
) -> CharacterService:
    return character_service_factory.create(
        character_repo=character_repo, user_repo=user_repo
    )

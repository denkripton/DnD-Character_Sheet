from fastapi import Depends

from src.dependencies import get_unit_of_work
from src.modules.character.dependencies import (
    character_ownership_guard,
    feature_repository,
)
from src.modules.character.features.service import FeatureService
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.modules.character.repositories import FeatureRepository
from src.utils.unit_of_work import UnitOfWork


def get_feature_service(
    ownership: CharacterOwnershipGuard = Depends(character_ownership_guard),
    feature_repo: FeatureRepository = Depends(feature_repository),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> FeatureService:
    return FeatureService(
        ownership_guard=ownership,
        feature_repository=feature_repo,
        unit_of_work=uow,
    )
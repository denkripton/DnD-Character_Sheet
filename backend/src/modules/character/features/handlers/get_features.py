from fastapi import Depends
from src.modules.auth import get_current_user
from src.modules.character.features.dependencies import get_feature_service
from src.modules.character.features.service import FeatureService


async def get_features(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: FeatureService = Depends(get_feature_service),
):
    return await service.get_features(user_id=user_id, character_id=character_id)

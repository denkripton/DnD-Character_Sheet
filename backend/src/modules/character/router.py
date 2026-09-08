from fastapi import APIRouter

from src.modules.character.base import router as base_router
from src.modules.character.stats import router as stats_router
from src.modules.character.combat import router as combat_router
from src.modules.character.saving_throws import router as saving_throws_router
from src.modules.character.skills import router as skills_router
from src.modules.character.proficiencies import router as proficiencies_router
from src.modules.character.features import router as features_router
from src.modules.character.personality import router as personality_router

character_router = APIRouter()

character_router.include_router(base_router)
character_router.include_router(stats_router)
character_router.include_router(combat_router)
character_router.include_router(saving_throws_router)
character_router.include_router(skills_router)
character_router.include_router(proficiencies_router)
character_router.include_router(features_router)
character_router.include_router(personality_router)
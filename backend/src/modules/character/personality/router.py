from fastapi import APIRouter
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.personality.handlers import (
    generate_personality,
    get_personality,
    set_personality,
)
from src.modules.character.personality.handlers.generate_personality import (
    router as generate_router,
)
from src.modules.character.personality.handlers.set_personality import (
    router as set_router,
)
from src.modules.character.personality.schemas import PersonalityReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/personality", route_class=ErrorHandlingRoute
)
router.get(
    "",
    summary="Get personality (Protected)",
    tags=["Personality CRUD's"],
    description="Get personality traits, ideals, bonds and flaws",
    response_model=PersonalityReadSchema | None,
    responses={401: {"model": User401}, 422: {"model": User422}},
)(get_personality)
router.include_router(set_router)
router.include_router(generate_router)

__all__ = ["generate_personality", "get_personality", "router", "set_personality"]

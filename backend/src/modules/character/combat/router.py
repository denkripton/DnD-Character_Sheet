from fastapi import APIRouter
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.combat.handlers import (
    generate_combat,
    get_combat,
    set_combat,
)
from src.modules.character.combat.handlers.generate_combat import (
    router as generate_router,
)
from src.modules.character.combat.handlers.set_combat import router as set_router
from src.modules.character.combat.schemas import CombatReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/combat", route_class=ErrorHandlingRoute
)
router.get(
    "",
    summary="Get combat info (Protected)",
    tags=["Combat CRUD's"],
    description="Get hit points, armor class, speed, etc.",
    response_model=CombatReadSchema | None,
    responses={401: {"model": User401}, 422: {"model": User422}},
)(get_combat)
router.include_router(set_router)
router.include_router(generate_router)

__all__ = ["generate_combat", "get_combat", "router", "set_combat"]

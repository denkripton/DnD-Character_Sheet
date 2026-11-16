from fastapi import APIRouter
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.proficiencies.handlers import (
    add_proficiency,
    delete_proficiency,
    generate_proficiencies,
    get_proficiencies,
    update_proficiency,
)
from src.modules.character.proficiencies.handlers.add_proficiency import (
    router as add_router,
)
from src.modules.character.proficiencies.handlers.delete_proficiency import (
    router as delete_router,
)
from src.modules.character.proficiencies.handlers.generate_proficiencies import (
    router as generate_router,
)
from src.modules.character.proficiencies.handlers.update_proficiency import (
    router as update_router,
)
from src.modules.character.proficiencies.schemas import ProficiencyReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/proficiencies", route_class=ErrorHandlingRoute
)
router.get(
    "",
    summary="Get all proficiencies (Protected)",
    tags=["Proficiencies CRUD's"],
    description="Get armor, weapon, tool proficiencies and languages",
    response_model=list[ProficiencyReadSchema],
    responses={401: {"model": User401}, 422: {"model": User422}},
)(get_proficiencies)
router.include_router(add_router)
router.include_router(generate_router)
router.include_router(update_router)
router.include_router(delete_router)

__all__ = [
    "add_proficiency",
    "delete_proficiency",
    "generate_proficiencies",
    "get_proficiencies",
    "router",
    "update_proficiency",
]

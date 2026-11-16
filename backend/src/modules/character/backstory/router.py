from fastapi import APIRouter
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.backstory.handlers import (
    generate_backstory,
    get_backstory,
    set_backstory,
)
from src.modules.character.backstory.handlers.generate_backstory import (
    router as generate_router,
)
from src.modules.character.backstory.handlers.set_backstory import router as set_router
from src.modules.character.backstory.schemas import BackstoryReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/backstory", route_class=ErrorHandlingRoute
)
router.get(
    "",
    summary="Get backstory (Protected)",
    tags=["Backstory CRUD's"],
    description="Get the long backstory of the character",
    response_model=BackstoryReadSchema | None,
    responses={401: {"model": User401}, 422: {"model": User422}},
)(get_backstory)
router.include_router(set_router)
router.include_router(generate_router)

__all__ = ["generate_backstory", "get_backstory", "router", "set_backstory"]

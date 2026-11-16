from fastapi import APIRouter
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.saving_throws.handlers import (
    generate_saving_throws,
    get_saving_throws,
    set_saving_throws,
)
from src.modules.character.saving_throws.handlers.generate_saving_throws import (
    router as generate_router,
)
from src.modules.character.saving_throws.handlers.set_saving_throws import (
    router as set_router,
)
from src.modules.character.saving_throws.schemas import SavingThrowsReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/saving-throws", route_class=ErrorHandlingRoute
)
router.get(
    "",
    summary="Get saving throws (Protected)",
    tags=["Saving Throws CRUD's"],
    description="Get which saving throws the character is proficient in",
    response_model=SavingThrowsReadSchema | None,
    responses={401: {"model": User401}, 422: {"model": User422}},
)(get_saving_throws)
router.include_router(set_router)
router.include_router(generate_router)

__all__ = ["generate_saving_throws", "get_saving_throws", "router", "set_saving_throws"]

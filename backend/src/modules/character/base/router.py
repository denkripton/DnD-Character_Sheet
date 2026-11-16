from fastapi import APIRouter
from src.modules.character.base.handlers import (
    character_by_id,
    create_character,
    delete_character,
    generate_character,
    get_my_characters,
    update_character,
)
from src.modules.character.base.handlers.character_by_id import router as by_id_router
from src.modules.character.base.handlers.create_character import router as create_router
from src.modules.character.base.handlers.delete_character import router as delete_router
from src.modules.character.base.handlers.generate_character import (
    router as generate_router,
)
from src.modules.character.base.handlers.get_my_characters import (
    router as my_characters_router,
)
from src.modules.character.base.handlers.update_character import router as update_router
from src.utils import ErrorHandlingRoute

router = APIRouter(prefix="/chatacters", route_class=ErrorHandlingRoute)
router.include_router(create_router)
router.include_router(generate_router)
router.include_router(my_characters_router)
router.include_router(by_id_router)
router.include_router(update_router)
router.include_router(delete_router)

__all__ = [
    "character_by_id",
    "create_character",
    "delete_character",
    "generate_character",
    "get_my_characters",
    "router",
    "update_character",
]

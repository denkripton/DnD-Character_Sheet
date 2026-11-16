from fastapi import APIRouter
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.skills.handlers import (
    add_skill,
    delete_skill,
    generate_skills,
    get_skills,
    update_skill,
)
from src.modules.character.skills.handlers.add_skill import router as add_router
from src.modules.character.skills.handlers.delete_skill import router as delete_router
from src.modules.character.skills.handlers.generate_skills import (
    router as generate_router,
)
from src.modules.character.skills.handlers.update_skill import router as update_router
from src.modules.character.skills.schemas import SkillReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(prefix="/chatacters/{character_id}/skills", route_class=ErrorHandlingRoute)
router.get(
    "",
    summary="Get all skills (Protected)",
    tags=["Skills CRUD's"],
    description="Get all skills of one of your characters",
    response_model=list[SkillReadSchema],
    responses={401: {"model": User401}, 422: {"model": User422}},
)(get_skills)
router.include_router(add_router)
router.include_router(generate_router)
router.include_router(update_router)
router.include_router(delete_router)

__all__ = [
    "add_skill",
    "delete_skill",
    "generate_skills",
    "get_skills",
    "router",
    "update_skill",
]

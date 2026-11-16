from fastapi import APIRouter
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.stats.handlers import (
    add_stats_yourself,
    generate_random_stats,
    get_stats,
)
from src.modules.character.stats.handlers.add_stats_yourself import router as add_router
from src.modules.character.stats.handlers.generate_random_stats import (
    router as generate_router,
)
from src.modules.character.stats.schemas.response import StatsResponseSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/stats", route_class=ErrorHandlingRoute
)
router.get(
    "",
    summary="Get character stats (Protected)",
    tags=["Stats CRUD's"],
    description="Get stats and modifiers of one of your characters",
    response_model=StatsResponseSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)(get_stats)
router.include_router(generate_router)
router.include_router(add_router)

__all__ = ["add_stats_yourself", "generate_random_stats", "get_stats", "router"]

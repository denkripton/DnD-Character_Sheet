from fastapi import APIRouter, Depends

from src.modules.ai.models import AVAILABLE_MODELS
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.utils import ErrorHandlingRoute

router = APIRouter(prefix="/ai", route_class=ErrorHandlingRoute)


@router.get(
    "/models",
    summary="List available AI models (Protected)",
    tags=["AI"],
    description=(
        "List the AI models the user can choose from when generating the "
        "backstory. The list is extended by adding model names to "
        "AVAILABLE_MODELS in src/modules/ai/models.py."
    ),
    response_model=list[str],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def list_models(
    user_id: str = Depends(get_current_user),
):
    return AVAILABLE_MODELS
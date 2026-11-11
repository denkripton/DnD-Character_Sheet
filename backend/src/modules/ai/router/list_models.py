from fastapi import APIRouter, Depends
from src.modules.ai.dependencies import get_models_catalog
from src.modules.ai.schemas import AIModelCatalogSchema
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.get(
    "/models",
    summary="List available AI models (Protected)",
    tags=["AI"],
    description="List all AI models available across registered providers",
    response_model=list[AIModelCatalogSchema],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def list_models(
    user_id: str = Depends(get_current_user),
    catalog: list[dict] = Depends(get_models_catalog),
):
    return [AIModelCatalogSchema(**item) for item in catalog]

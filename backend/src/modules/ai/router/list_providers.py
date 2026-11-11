from fastapi import APIRouter, Depends
from src.modules.ai.dependencies import get_providers_catalog
from src.modules.ai.schemas import AIProviderCatalogSchema
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.get(
    "/providers",
    summary="List available AI providers (Protected)",
    tags=["AI"],
    description="List all registered AI providers and their supported models",
    response_model=list[AIProviderCatalogSchema],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def list_providers(
    user_id: str = Depends(get_current_user),
    catalog: list[dict] = Depends(get_providers_catalog),
):
    return [AIProviderCatalogSchema(**item) for item in catalog]

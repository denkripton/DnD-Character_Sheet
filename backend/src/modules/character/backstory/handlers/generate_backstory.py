from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.backstory.dependencies import get_backstory_service
from src.modules.character.backstory.schemas import BackstoryReadSchema
from src.modules.character.backstory.service import BackstoryService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/generate",
    summary="Generate backstory with AI (Protected)",
    tags=["Backstory CRUD's"],
    description=(
        "Generate a long backstory with Gemini using the character's name, "
        "race, class, background, personality and all of its features, then "
        "save it. The 'model' query parameter selects one of the models listed "
        "by GET /ai/models (defaults to the first one). Story must be 500-700 "
        "symbols long; longer than 1000 symbols returns an error."
    ),
    response_model=BackstoryReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_backstory(
    character_id: str,
    model: str | None = None,
    provider: str | None = None,
    user_id: str = Depends(get_current_user),
    service: BackstoryService = Depends(get_backstory_service),
):
    return await service.generate_backstory(
        user_id=user_id,
        character_id=character_id,
        model=model,
        provider=provider,
    )

from fastapi import APIRouter, Depends
from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.draft import CharacterDraftReadSchema
from src.modules.character.draft.dependencies import get_character_draft_service
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/generate",
    summary="Generate a random character (Protected)",
    tags=["Character CRUD's"],
    description=(
        "Generate a character with a random name, class, species, alignment "
        "and background as a draft. Save it explicitly before it becomes a character."
    ),
    response_model=CharacterDraftReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_character(
    user_id: str = Depends(get_current_user),
    service=Depends(get_character_draft_service),
):
    draft = await service.create_draft(user_id=user_id)
    result = await service.generate_character(
        user_id=user_id, draft_id=draft.id, method="random"
    )
    return result["draft"]

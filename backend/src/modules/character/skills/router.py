from fastapi import APIRouter, Depends

from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.skills.schemas import SkillCreateSchema, SkillReadSchema
from src.modules.character.skills.dependencies import get_skill_service
from src.modules.character.skills.service import SkillService
from src.utils import ErrorHandlingRoute

router = APIRouter(prefix="/chatacters/{character_id}/skills", route_class=ErrorHandlingRoute)


@router.get(
    "",
    summary="Get all skills (Protected)",
    tags=["Skills CRUD's"],
    description="Get all skills of one of your characters",
    response_model=list[SkillReadSchema],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def get_skills(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
):
    return await service.get_skills(user_id=user_id, character_id=character_id)


@router.post(
    "/create",
    summary="Add a skill (Protected)",
    tags=["Skills CRUD's"],
    description="Add a skill to your character",
    response_model=SkillReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def add_skill(
    character_id: str,
    data: SkillCreateSchema,
    user_id: str = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
):
    return await service.add_skill(
        user_id=user_id, character_id=character_id, data=data
    )


@router.put(
    "/{skill_id}",
    summary="Update a skill (Protected)",
    tags=["Skills CRUD's"],
    description="Update one of the character's skills",
    response_model=SkillReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def update_skill(
    character_id: str,
    skill_id: str,
    data: SkillCreateSchema,
    user_id: str = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
):
    return await service.update_skill(
        user_id=user_id, character_id=character_id, skill_id=skill_id, data=data
    )


@router.delete(
    "/{skill_id}",
    summary="Delete a skill (Protected)",
    tags=["Skills CRUD's"],
    description="Delete one of the character's skills",
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def delete_skill(
    character_id: str,
    skill_id: str,
    user_id: str = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
):
    return await service.delete_skill(
        user_id=user_id, character_id=character_id, skill_id=skill_id
    )
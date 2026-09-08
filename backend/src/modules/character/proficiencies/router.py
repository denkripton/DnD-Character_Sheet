from fastapi import APIRouter, Depends, Query

from src.modules.auth import get_current_user
from src.modules.auth.schemas.exceptions.user_401 import User401
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.character.proficiencies.dependencies import get_proficiency_service
from src.modules.character.proficiencies.service import ProficiencyService
from src.modules.character.proficiencies.schemas import ProficiencyCreateSchema, ProficiencyReadSchema
from src.utils import ErrorHandlingRoute

router = APIRouter(
    prefix="/chatacters/{character_id}/proficiencies", route_class=ErrorHandlingRoute
)


@router.get(
    "",
    summary="Get all proficiencies (Protected)",
    tags=["Proficiencies CRUD's"],
    description="Get armor, weapon, tool proficiencies and languages",
    response_model=list[ProficiencyReadSchema],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def get_proficiencies(
    character_id: str,
    user_id: str = Depends(get_current_user),
    service: ProficiencyService = Depends(get_proficiency_service),
):
    return await service.get_proficiencies(user_id=user_id, character_id=character_id)


@router.post(
    "/create",
    summary="Add a proficiency (Protected)",
    tags=["Proficiencies CRUD's"],
    description="Add armor, weapon, tool proficiency or a language",
    response_model=ProficiencyReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def add_proficiency(
    character_id: str,
    data: ProficiencyCreateSchema,
    user_id: str = Depends(get_current_user),
    service: ProficiencyService = Depends(get_proficiency_service),
):
    return await service.add_proficiency(
        user_id=user_id, character_id=character_id, data=data
    )


@router.post(
    "/generate",
    summary="Generate random proficiencies (Protected)",
    tags=["Proficiencies CRUD's"],
    description=(
        "Add a random set of armor, weapon, tool proficiencies and languages "
        "(2-4 by default). Already known proficiencies are skipped."
    ),
    response_model=list[ProficiencyReadSchema],
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def generate_proficiencies(
    character_id: str,
    count: int | None = Query(
        default=None,
        ge=1,
        le=20,
        description="How many proficiencies to generate (default: random 2-4)",
    ),
    user_id: str = Depends(get_current_user),
    service: ProficiencyService = Depends(get_proficiency_service),
):
    return await service.generate_proficiencies(
        user_id=user_id, character_id=character_id, count=count
    )


@router.put(
    "/{proficiency_id}",
    summary="Update a proficiency (Protected)",
    tags=["Proficiencies CRUD's"],
    description="Update one of the character's proficiencies",
    response_model=ProficiencyReadSchema,
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def update_proficiency(
    character_id: str,
    proficiency_id: str,
    data: ProficiencyCreateSchema,
    user_id: str = Depends(get_current_user),
    service: ProficiencyService = Depends(get_proficiency_service),
):
    return await service.update_proficiency(
        user_id=user_id,
        character_id=character_id,
        proficiency_id=proficiency_id,
        data=data,
    )


@router.delete(
    "/{proficiency_id}",
    summary="Delete a proficiency (Protected)",
    tags=["Proficiencies CRUD's"],
    description="Delete one of the character's proficiencies",
    responses={
        401: {"model": User401},
        422: {"model": User422},
    },
)
async def delete_proficiency(
    character_id: str,
    proficiency_id: str,
    user_id: str = Depends(get_current_user),
    service: ProficiencyService = Depends(get_proficiency_service),
):
    return await service.delete_proficiency(
        user_id=user_id,
        character_id=character_id,
        proficiency_id=proficiency_id,
    )
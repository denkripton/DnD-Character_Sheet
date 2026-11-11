from fastapi import APIRouter, Depends
from src.modules.auth.dependencies import get_user_service
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.auth.schemas.user.creation import UserCreateSchema
from src.modules.auth.schemas.user.read import UserRead
from src.modules.auth.service import UserService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/register",
    summary="Registration",
    tags=["User CRUD's"],
    description="Registrate user",
    response_model=UserRead,
    responses={
        422: {"model": User422},
    },
)
async def register_user(
    data: UserCreateSchema,
    service: UserService = Depends(get_user_service),
):
    return await service.register(data=data)

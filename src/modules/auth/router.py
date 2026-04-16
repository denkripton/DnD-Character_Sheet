from fastapi import APIRouter, Depends

from src.dependencies import get_error
from src.modules.auth import get_user_service
from src.modules.auth.service import UserService

from src.modules.auth.schemas.user.read import UserRead
from src.modules.auth.schemas.user.creation import UserCreateSchema

from src.modules.auth.schemas.exceptions.user_422 import User422


user_router = APIRouter(prefix="/users")


@user_router.post(
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
    return await get_error(service.register, data=data)
from fastapi import APIRouter, Depends, Response
from src.modules.auth.dependencies import get_user_service
from src.modules.auth.schemas.auth.read import AuthReadSchema
from src.modules.auth.schemas.exceptions.password_403 import Password403
from src.modules.auth.schemas.exceptions.user_422 import User422
from src.modules.auth.schemas.user.login import UserLoginSchema
from src.modules.auth.service import UserService
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/login",
    summary="Authenticate",
    tags=["Authentication"],
    description="Login user",
    response_model=AuthReadSchema,
    responses={
        403: {"model": Password403},
        422: {"model": User422},
    },
)
async def login_user(
    data: UserLoginSchema,
    response: Response,
    service: UserService = Depends(get_user_service),
):
    user = await service.login(data=data)

    response.set_cookie(
        key="refresh_token",
        value=user["refresh"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )

    return user

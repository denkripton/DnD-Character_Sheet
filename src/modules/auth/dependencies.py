from typing import Optional

from fastapi import Depends, Request, Response, HTTPException

from src.modules.auth.service import UserService
from src.modules.auth.repository import UserRepository
from src.dependencies import RepoFactory
from src.modules.auth.utils import JWT


user_repository = RepoFactory(repo=UserRepository)

def get_jwt() -> JWT:
    return JWT()


class UserServiceFactory:
    def __call__(
        self, 
        repo: UserRepository = Depends(user_repository),
        jwt: JWT = Depends(get_jwt)
        ):
        return UserService(user_repository=repo, jwt=jwt)

get_user_service = UserServiceFactory()


async def get_current_user(
    request: Request, response: Response, jwt: JWT = Depends(get_jwt)
):
    auth_header: Optional[str] = request.headers.get("Authorization")
    token = auth_header.replace("Bearer", "") if auth_header else None

    payload = jwt.validate_token(token)

    if payload:
        return payload["sub"]

    get_refresh_token = request.cookies.get("refresh_token")
    refresh_token = jwt.validate_token(get_refresh_token)

    if refresh_token is None:
        raise HTTPException(status_code=401, detail="User not authorized")

    new_access_token = jwt.create_access_token(refresh_token["sub"])

    response.headers["X-New-Access-Token"] = new_access_token

    return refresh_token["sub"]
from fastapi import Depends, HTTPException, Request, Response
from src.modules.auth.dependencies.get_jwt_service import get_jwt_service
from src.modules.auth.utils import JWT


async def get_current_user(
    request: Request, response: Response, jwt: JWT = Depends(get_jwt_service)
):
    auth_header: str | None = request.headers.get("Authorization")
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

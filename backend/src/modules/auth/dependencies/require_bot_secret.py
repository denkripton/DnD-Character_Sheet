import hmac

from fastapi import HTTPException, Request
from src.config import settings
from src.modules.auth.dependencies.bot_secret_header import BOT_SECRET_HEADER


def require_bot_secret(request: Request) -> None:
    provided = request.headers.get(BOT_SECRET_HEADER)
    expected = settings.BOT_API_SECRET
    if not provided or not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid bot secret")

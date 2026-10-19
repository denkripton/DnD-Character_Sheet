import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from src.utils.exceptions import ServiceError


def validate_telegram_init_data(
    init_data: str,
    bot_token: str | None,
    max_age_seconds: int = 300,
    now: int | None = None,
) -> dict:
    if not bot_token:
        raise ServiceError(code=503, msg="Telegram authentication is not configured")
    try:
        fields = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
        values = dict(fields)
        if len(values) != len(fields):
            raise ValueError
        supplied_hash = values.pop("hash")
        auth_date = int(values["auth_date"])
        user = json.loads(values["user"])
        current_time = int(time.time()) if now is None else now
        if auth_date > current_time or current_time - auth_date > max_age_seconds:
            raise ValueError
        if not isinstance(user, dict) or not isinstance(user.get("id"), int) or user["id"] <= 0:
            raise ValueError
        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(values.items())
        )
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()
        expected_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, supplied_hash):
            raise ValueError
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise ServiceError(code=401, msg="Invalid Telegram initData") from None
    return user

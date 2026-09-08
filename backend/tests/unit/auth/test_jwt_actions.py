import time

from src.modules.auth.utils.jwt_actions import JWT


def test_access_token_roundtrip():
    jwt = JWT()
    token = jwt.create_access_token("user-1")
    payload = jwt.decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["iat"] > 0
    assert payload["exp"] > payload["iat"]


def test_refresh_token_roundtrip():
    jwt = JWT()
    token = jwt.create_refresh_token("user-1")
    payload = jwt.decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["exp"] > payload["iat"]


def test_refresh_token_custom_expiration():
    jwt = JWT()
    custom_exp = int(time.time()) + 3600
    token = jwt.create_refresh_token("user-1", expiration=custom_exp)
    payload = jwt.decode_token(token)
    assert payload["exp"] == custom_exp


def test_validate_token_returns_payload():
    jwt = JWT()
    token = jwt.create_access_token("user-1")
    payload = jwt.validate_token(token)
    assert payload is not None
    assert payload["sub"] == "user-1"


def test_validate_none_token_returns_none():
    jwt = JWT()
    assert jwt.validate_token(None) is None


def test_validate_empty_token_returns_none():
    jwt = JWT()
    assert jwt.validate_token("") is None


def test_validate_garbage_token_returns_none():
    jwt = JWT()
    assert jwt.validate_token("not-a-token") is None


def test_validate_expired_token_returns_none():
    jwt = JWT()
    expired = jwt.create_token({"sub": "user-1", "iat": 0, "exp": 1})
    assert jwt.validate_token(expired) is None


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("jwt actions tests passed")
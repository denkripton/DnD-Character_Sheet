from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from src.config import settings
from src.modules.auth.dependencies import BOT_SECRET_HEADER, require_bot_secret


def _request(headers=None):
    return SimpleNamespace(headers=headers or {})


def test_require_bot_secret_accepts_matching_secret(monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_SECRET", "top-secret")
    require_bot_secret(_request({BOT_SECRET_HEADER: "top-secret"}))


def test_require_bot_secret_rejects_wrong_secret(monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_SECRET", "top-secret")
    with pytest.raises(HTTPException) as exc_info:
        require_bot_secret(_request({BOT_SECRET_HEADER: "wrong"}))
    assert exc_info.value.status_code == 401


def test_require_bot_secret_rejects_missing_header(monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_SECRET", "top-secret")
    with pytest.raises(HTTPException) as exc_info:
        require_bot_secret(_request())
    assert exc_info.value.status_code == 401


def test_require_bot_secret_rejects_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_SECRET", "")
    with pytest.raises(HTTPException) as exc_info:
        require_bot_secret(_request({BOT_SECRET_HEADER: "anything"}))
    assert exc_info.value.status_code == 401
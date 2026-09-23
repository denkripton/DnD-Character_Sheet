from types import SimpleNamespace

import pytest
from app.modules.start.schemas.user import UserIdentity
from app.utils.schemas.base_schema import BaseSchema
from pydantic import ValidationError


def test_from_aiogram():
    user = UserIdentity.from_aiogram(
        SimpleNamespace(id=7, username="hero", first_name="Hana"),
    )
    assert user.id == 7
    assert user.username == "hero"
    assert user.first_name == "Hana"


def test_from_aiogram_none():
    assert UserIdentity.from_aiogram(None).id == 0


def test_from_aiogram_missing_optional_fields():
    user = UserIdentity.from_aiogram(SimpleNamespace(id=7, first_name="Hana"))
    assert user.username is None


def test_user_identity_inherits_base_schema():
    assert issubclass(UserIdentity, BaseSchema)


def test_model_validate_reads_attributes():
    identity = UserIdentity.model_validate(
        SimpleNamespace(id=7, username="hero", first_name="Hana", is_bot=False),
    )
    assert identity.id == 7
    assert identity.username == "hero"
    assert identity.first_name == "Hana"


def test_user_identity_forbids_extra_fields():
    with pytest.raises(ValidationError):
        UserIdentity(id=7, unknown="x")
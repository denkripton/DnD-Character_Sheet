from app.schemas.base import BaseSchema


class UserIdentity(BaseSchema):
    id: int
    username: str | None = None
    first_name: str = ""

    @classmethod
    def from_aiogram(cls, user) -> "UserIdentity":
        if user is None:
            return cls(id=0)
        return cls.model_validate(user)

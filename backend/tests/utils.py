import uuid

from src.modules.character.models import Character
from src.modules.character.utils.ownership import CharacterOwnershipGuard


class FakeSession:
    async def commit(self):
        pass

    async def refresh(self, obj):
        return obj


class FakeRepo:
    def __init__(self, model):
        self.model = model
        self.session = FakeSession()
        self.rows = []

    async def get_by_id(self, id):
        return next((r for r in self.rows if getattr(r, "id", None) == id), None)

    async def get_by_email(self, email):
        return next((r for r in self.rows if getattr(r, "email", None) == email), None)

    async def get_one(self, **kwargs):
        for row in self.rows:
            if all(
                value is None or getattr(row, key, None) == value
                for key, value in kwargs.items()
            ):
                return row
        return None

    async def get_many(self, skip: int = 0, limit: int = None, **kwargs):
        rows = [
            row
            for row in self.rows
            if all(
                value is None or getattr(row, key, None) == value
                for key, value in kwargs.items()
            )
        ]
        if limit is None:
            return rows[skip:]
        return rows[skip : skip + limit]

    async def create(self, **kwargs):
        if kwargs.get("id") is None:
            kwargs["id"] = uuid.uuid4()
        obj = self.model(**kwargs)
        self.rows.append(obj)
        return obj

    async def delete_obj(self, id):
        row = next(r for r in self.rows if getattr(r, "id", None) == id)
        self.rows.remove(row)
        return row


def build_guard(character_repo, user_repo, user_id):
    user = type("User", (), {"id": user_id})()
    user_repo.rows.append(user)
    return CharacterOwnershipGuard(
        character_repository=character_repo,
        user_repository=user_repo,
    )


def build_owned_character(
    character_repo,
    character_id=None,
    owner_id="user-1",
    spec_class="Barbarian",
    kind="Human",
):
    character = Character(
        id=character_id or uuid.uuid4(),
        name="Grog",
        spec_class=spec_class,
        kind=kind,
        level=1,
        experience_points=0,
        owner_id=owner_id,
    )
    character_repo.rows.append(character)
    return character
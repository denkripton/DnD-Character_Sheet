from uuid import UUID

from pydantic import ValidationError
from src.modules.auth.repository import UserRepository
from src.modules.character.base.schemas import CharacterUpdateSchema
from src.modules.character.draft.schemas import CharacterDraftReadSchema
from src.modules.character.models import CharacterDraft
from src.modules.character.repositories import CharacterDraftRepository
from src.modules.character.utils.random_character import generate_random_character
from src.utils.exceptions import ServiceError
from src.utils.unit_of_work import UnitOfWork

PARAMETER_LABELS = {
    "name": "Name",
    "kind": "Race",
    "spec_class": "Class",
    "alignment": "Alignment",
    "background": "Background",
    "level": "Level",
    "experience_points": "Experience points",
}


def parameter_label(parameter: str) -> str:
    return PARAMETER_LABELS.get(parameter, parameter)


def friendly_validation_message(exc: ValidationError) -> str:
    error = exc.errors()[0]
    location = error.get("loc") or ()
    field = str(location[0]) if location else ""
    label = parameter_label(field)
    error_type = error.get("type")
    if error_type == "string_too_long":
        max_length = error.get("ctx", {}).get("max_length")
        return f"{label} must be no more than {max_length} characters."
    if error_type == "extra_forbidden":
        return f"Unsupported parameter: {field}."
    if error_type == "string_type":
        return f"{label} must be a text value."
    if error_type == "missing":
        return f"{label} is required."
    return f"{label}: {error.get('msg', 'is invalid')}."


class CharacterDraftService:
    def __init__(
        self,
        draft_repository: CharacterDraftRepository,
        user_repository: UserRepository,
        unit_of_work: UnitOfWork,
    ):
        self.draft_repo = draft_repository
        self.user_repo = user_repository
        self.uow = unit_of_work

    async def _get_owned(self, user_id: str, draft_id) -> CharacterDraft:
        try:
            identifier = UUID(str(draft_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ServiceError(
                msg="Character draft not found. Start a new character with /create_character.",
                code=422,
            ) from exc
        draft = await self.draft_repo.get_one(id=identifier, owner_id=user_id)
        if draft is None:
            raise ServiceError(
                msg="Character draft not found. Start a new character with /create_character.",
                code=422,
            )
        return draft

    def _validate_parameter(self, parameter: str, value) -> dict:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ServiceError(
                msg=f"{parameter_label(parameter)} cannot be empty.", code=422
            )
        try:
            validated = CharacterUpdateSchema(**{parameter: value})
        except ValidationError as exc:
            raise ServiceError(msg=friendly_validation_message(exc), code=422) from exc
        data = validated.model_dump(exclude_none=True)
        if parameter not in data:
            raise ServiceError(
                msg=f"{parameter_label(parameter)} cannot be empty.", code=422
            )
        return data

    async def _apply(
        self, draft: CharacterDraft, parameter: str, value
    ) -> CharacterDraftReadSchema:
        data = self._validate_parameter(parameter, value)
        draft.data = {**(draft.data or {}), **data}
        await self.uow.commit()
        await self.uow.refresh(draft)
        return CharacterDraftReadSchema.model_validate(draft)

    async def create_draft(self, user_id: str) -> CharacterDraftReadSchema:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise ServiceError(msg="User does not exist", code=422)

        draft = await self.draft_repo.create(owner_id=user_id, data={})
        await self.uow.commit()
        await self.uow.refresh(draft)
        return CharacterDraftReadSchema.model_validate(draft)

    async def update_parameter(
        self, user_id: str, draft_id, parameter: str, value
    ) -> CharacterDraftReadSchema:
        draft = await self._get_owned(user_id, draft_id)
        return await self._apply(draft, parameter, value)

    async def generate_parameter(
        self, user_id: str, draft_id, parameter: str
    ) -> CharacterDraftReadSchema:
        draft = await self._get_owned(user_id, draft_id)
        generated = generate_random_character()
        if parameter not in generated:
            raise ServiceError(
                msg=f"Generation is not supported for {parameter_label(parameter)}.",
                code=422,
            )
        return await self._apply(draft, parameter, generated[parameter])

    async def delete_draft(self, user_id: str, draft_id) -> None:
        draft = await self._get_owned(user_id, draft_id)
        await self.draft_repo.delete_obj(draft.id)
        await self.uow.commit()

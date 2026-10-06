from uuid import UUID

from pydantic import ValidationError
from src.modules.auth.repository import UserRepository
from src.modules.character.base.schemas import CharacterUpdateSchema
from src.modules.character.draft.schemas import CharacterDraftReadSchema
from src.modules.character.models import CharacterDraft
from src.modules.character.repositories import CharacterDraftRepository
from src.modules.character.stats.schemas import StatsCreateSchema
from src.modules.character.utils import (
    assign_stats,
    compute_modifiers,
    generate_point_buy_stats,
    generate_random_stats,
    generate_standard_array,
)
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


def _parse_stats_values(values) -> dict:
    if not isinstance(values, (list, tuple)) or len(values) != 6:
        raise ServiceError(
            msg="Enter exactly six values in order: STR DEX CON INT WIS CHA.",
            code=422,
        )
    parsed = []
    for value in values:
        try:
            parsed.append(int(str(value).strip()))
        except (TypeError, ValueError) as exc:
            raise ServiceError(msg="Stats must be whole numbers.", code=422) from exc
    return assign_stats(parsed)


def _stats_error_message(exc: ValidationError) -> str:
    error = exc.errors()[0]
    error_type = error.get("type")
    if error_type in ("greater_than_equal", "less_than_equal"):
        return "Each stat must be between 8 and 15."
    if error_type == "value_error":
        message = str(error.get("msg", ""))
        message = message.removeprefix("Value error, ")
        return message
    if error_type == "int_type":
        return "Stats must be whole numbers."
    if error_type == "missing":
        return "All six stats are required."
    return str(error.get("msg", "Stats are invalid."))


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

    async def generate_stats(self, user_id: str, draft_id, method: str) -> dict:
        draft = await self._get_owned(user_id, draft_id)
        if method == "standard":
            generated = generate_standard_array()
        elif method == "point_buy":
            generated = generate_point_buy_stats()
        elif method == "random":
            generated = generate_random_stats()
        else:
            raise ServiceError(
                msg=f"Unsupported stats generation method: {method}.", code=422
            )
        stats_dict = assign_stats(generated)
        await self._store_stats(draft, stats_dict)
        return {"stats": stats_dict, "modifiers": compute_modifiers(stats_dict)}

    async def set_stats(self, user_id: str, draft_id, values) -> dict:
        draft = await self._get_owned(user_id, draft_id)
        stats_dict = _parse_stats_values(values)
        try:
            StatsCreateSchema(**stats_dict)
        except ValidationError as exc:
            raise ServiceError(msg=_stats_error_message(exc), code=422) from exc
        await self._store_stats(draft, stats_dict)
        return {"stats": stats_dict, "modifiers": compute_modifiers(stats_dict)}

    async def _store_stats(self, draft: CharacterDraft, stats_dict: dict) -> None:
        draft.data = {**(draft.data or {}), "stats": stats_dict}
        await self.uow.commit()
        await self.uow.refresh(draft)

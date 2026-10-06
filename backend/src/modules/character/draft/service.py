import uuid
from uuid import UUID

from pydantic import ValidationError
from src.config import settings
from src.infrastructure.redis import cache
from src.modules.auth.repository import UserRepository
from src.modules.character.base.enums.generation_limits import GenerationLimits
from src.modules.character.base.schemas import (
    CharacterCreateSchema,
    CharacterReadSchema,
    CharacterUpdateSchema,
)
from src.modules.character.draft.schemas import CharacterDraftReadSchema
from src.modules.character.models import CharacterDraft
from src.modules.character.repositories import (
    CharacterDraftRepository,
    CharacterRepository,
    StatsRepository,
)
from src.modules.character.stats.schemas import StatsCreateSchema
from src.modules.character.utils import (
    assign_stats,
    compute_modifiers,
    generate_point_buy_stats,
    generate_random_stats,
    generate_standard_array,
)
from src.modules.character.utils.random_character import generate_random_character
from src.utils.exceptions import RateLimitExceeded, ServiceError
from src.utils.interfaces.rate_limiter import RateLimiter
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

FULL_GENERATION_METHODS = ("random", "standard", "point_buy")

DAILY_LIMIT_COUNTED_OPERATIONS = frozenset({"generate_character", "save_character"})

CHARACTER_DRAFT_FIELDS = (
    "name",
    "kind",
    "spec_class",
    "alignment",
    "background",
    "level",
    "experience_points",
)

STAT_FIELDS = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)


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


def _draft_stats_values(stats) -> dict:
    if not isinstance(stats, dict):
        raise ServiceError(msg="Ability scores are invalid.", code=422)
    values = {}
    for field in STAT_FIELDS:
        value = stats.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not 3 <= value <= 20:
            raise ServiceError(
                msg="Ability scores must be whole numbers between 3 and 20.",
                code=422,
            )
        values[field] = value
    return values


class CharacterDraftService:
    def __init__(
        self,
        draft_repository: CharacterDraftRepository,
        character_repository: CharacterRepository,
        stats_repository: StatsRepository,
        user_repository: UserRepository,
        unit_of_work: UnitOfWork,
        rate_limiter: RateLimiter,
    ):
        self.draft_repo = draft_repository
        self.character_repo = character_repository
        self.stats_repo = stats_repository
        self.user_repo = user_repository
        self.uow = unit_of_work
        self.rate_limiter = rate_limiter

    async def _enforce_daily_generation_limit(
        self, user_id: str, operation: str
    ) -> None:
        if operation not in DAILY_LIMIT_COUNTED_OPERATIONS:
            return
        result = await self.rate_limiter.is_limited(
            user_id=user_id,
            category=GenerationLimits.KEY_PREFIX.value,
            max_requests=settings.CHARACTER_GENERATION_DAILY_LIMIT,
            time_window=GenerationLimits.DAILY_WINDOW_SECONDS.value,
        )
        if not result.allowed:
            raise RateLimitExceeded(
                limit=result.max_allowed,
                used=result.current_usage,
                retry_after=result.retry_after,
            )

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
        await self._enforce_daily_generation_limit(user_id, "create_draft")
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
        await self._enforce_daily_generation_limit(user_id, "update_parameter")
        draft = await self._get_owned(user_id, draft_id)
        return await self._apply(draft, parameter, value)

    async def generate_parameter(
        self, user_id: str, draft_id, parameter: str
    ) -> CharacterDraftReadSchema:
        await self._enforce_daily_generation_limit(user_id, "generate_parameter")
        draft = await self._get_owned(user_id, draft_id)
        generated = generate_random_character()
        if parameter not in generated:
            raise ServiceError(
                msg=f"Generation is not supported for {parameter_label(parameter)}.",
                code=422,
            )
        return await self._apply(draft, parameter, generated[parameter])

    async def delete_draft(self, user_id: str, draft_id) -> None:
        await self._enforce_daily_generation_limit(user_id, "delete_draft")
        draft = await self._get_owned(user_id, draft_id)
        await self.draft_repo.delete_obj(draft.id)
        await self.uow.commit()

    async def save_character(self, user_id: str, draft_id) -> dict:
        await self._enforce_daily_generation_limit(user_id, "save_character")
        draft = await self._get_owned(user_id, draft_id)
        data = draft.data or {}
        payload = {
            field: data[field]
            for field in CHARACTER_DRAFT_FIELDS
            if field in data
        }
        try:
            validated = CharacterCreateSchema(**payload)
        except ValidationError as exc:
            raise ServiceError(
                msg=friendly_validation_message(exc), code=422
            ) from exc

        stats = data.get("stats")
        stats_values = _draft_stats_values(stats) if stats else None

        character = await self.character_repo.create(
            id=uuid.uuid4(),
            owner_id=user_id,
            **validated.model_dump(),
        )
        if stats_values is not None:
            await self.stats_repo.create(
                character_id=character.id, **stats_values
            )
        await self.draft_repo.delete_obj(draft.id)
        await self.uow.commit()
        await self.uow.refresh(character)

        await cache.delete_pattern(f"characters:list:{user_id}*")

        return {
            "character_id": str(character.id),
            "character": CharacterReadSchema.model_validate(character).model_dump(
                mode="json"
            ),
        }

    async def generate_character(
        self, user_id: str, draft_id, method: str
    ) -> dict:
        await self._enforce_daily_generation_limit(user_id, "generate_character")
        draft = await self._get_owned(user_id, draft_id)
        if method not in FULL_GENERATION_METHODS:
            raise ServiceError(
                msg=(
                    f"Unsupported generation method: {method}. "
                    "Manual stats are available in step-by-step creation."
                ),
                code=422,
            )
        generated = generate_random_character()
        stats_dict = _generate_stats_values(method)
        draft.data = {**(draft.data or {}), **generated, "stats": stats_dict}
        await self.uow.commit()
        await self.uow.refresh(draft)
        return {
            "draft": CharacterDraftReadSchema.model_validate(draft),
            "stats": stats_dict,
            "modifiers": compute_modifiers(stats_dict),
        }

    async def generate_stats(self, user_id: str, draft_id, method: str) -> dict:
        await self._enforce_daily_generation_limit(user_id, "generate_stats")
        draft = await self._get_owned(user_id, draft_id)
        stats_dict = _generate_stats_values(method)
        await self._store_stats(draft, stats_dict)
        return {"stats": stats_dict, "modifiers": compute_modifiers(stats_dict)}

    async def set_stats(self, user_id: str, draft_id, values) -> dict:
        await self._enforce_daily_generation_limit(user_id, "set_stats")
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


def _generate_stats_values(method: str) -> dict:
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
    return assign_stats(generated)

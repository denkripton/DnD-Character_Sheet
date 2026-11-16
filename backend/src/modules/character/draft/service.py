from uuid import UUID

import structlog
from pydantic import ValidationError
from src.config import settings
from src.databases.unit_of_work import UnitOfWork
from src.infrastructure.redis import cache
from src.modules.auth.repository import UserRepository
from src.modules.character.base.enums.generation_limits import GenerationLimits
from src.modules.character.base.schemas import (
    CharacterCreateSchema,
    CharacterReadSchema,
    CharacterUpdateSchema,
)
from src.modules.character.draft.constants import PARAMETER_LABELS
from src.modules.character.draft.fields import CHARACTER_DRAFT_FIELDS, STAT_FIELDS
from src.modules.character.draft.helpers import (
    _draft_stats_values,
    _generate_stats_values,
    _parse_stats_values,
    _stats_error_message,
    friendly_validation_message,
    parameter_label,
)
from src.modules.character.draft.schemas import CharacterDraftReadSchema
from src.modules.character.models import CharacterDraft
from src.modules.character.repositories import (
    BackstoryRepository,
    CharacterDraftRepository,
    CharacterRepository,
    CombatRepository,
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
from src.modules.character.utils.hit_points import recalculate_combat_hit_dice
from src.modules.character.utils.ownership import coerce_identifier
from src.modules.character.utils.random_character import generate_random_character
from src.utils.exceptions import RateLimitExceeded, ServiceError
from src.utils.interfaces.rate_limiter import RateLimiter

FULL_GENERATION_METHODS = ("random", "standard", "point_buy")
logger = structlog.get_logger(__name__)

DAILY_LIMIT_COUNTED_OPERATIONS = frozenset({"generate_character", "save_character"})

__all__ = [
    "PARAMETER_LABELS",
    "CharacterDraftService",
    "assign_stats",
    "generate_point_buy_stats",
    "generate_random_stats",
    "generate_standard_array",
]


class CharacterDraftService:
    def __init__(
        self,
        draft_repository: CharacterDraftRepository,
        character_repository: CharacterRepository,
        stats_repository: StatsRepository,
        user_repository: UserRepository,
        unit_of_work: UnitOfWork,
        rate_limiter: RateLimiter,
        combat_repository: CombatRepository,
        backstory_repository: BackstoryRepository | None = None,
    ):
        self.draft_repo = draft_repository
        self.character_repo = character_repository
        self.stats_repo = stats_repository
        self.user_repo = user_repository
        self.uow = unit_of_work
        self.rate_limiter = rate_limiter
        self.combat_repo = combat_repository
        self.backstory_repo = backstory_repository

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
        draft = await self.draft_repo.get_one(
            id=identifier, owner_id=coerce_identifier(user_id)
        )
        if draft is None:
            raise ServiceError(
                msg="Character draft not found. Start a new character with /create_character.",
                code=422,
            )
        if draft.saved_character_id is not None:
            raise ServiceError(
                msg="This character draft has already been saved.", code=422
            )
        return draft

    @staticmethod
    def _saved_result(character) -> dict:
        return {
            "character_id": str(character.id),
            "character": CharacterReadSchema.model_validate(character).model_dump(
                mode="json"
            ),
        }

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
        user = await self.user_repo.get_by_id(coerce_identifier(user_id))
        if user is None:
            raise ServiceError(msg="User does not exist", code=422)

        draft = await self.draft_repo.create(
            owner_id=coerce_identifier(user_id), data={}
        )
        await self.uow.commit()
        await self.uow.refresh(draft)
        return CharacterDraftReadSchema.model_validate(draft)

    async def create_edit_draft(
        self, user_id: str, character_id
    ) -> CharacterDraftReadSchema:
        try:
            identifier = UUID(str(character_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ServiceError(msg="Character not found.", code=422) from exc
        character = await self.character_repo.get_one(
            id=identifier, owner_id=coerce_identifier(user_id)
        )
        if character is None:
            raise ServiceError(msg="Character not found.", code=422)
        data = {field: getattr(character, field) for field in CHARACTER_DRAFT_FIELDS}
        stats = await self.stats_repo.get_one(character_id=identifier)
        if stats is not None:
            data["stats"] = {field: getattr(stats, field) for field in STAT_FIELDS}
        draft = await self.draft_repo.create(
            owner_id=coerce_identifier(user_id),
            target_character_id=identifier,
            data=data,
        )
        await self.uow.commit()
        await self.uow.refresh(draft)
        return CharacterDraftReadSchema.model_validate(draft).model_copy(
            update={"modifiers": compute_modifiers(data["stats"]) if stats else None}
        )

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

    async def save_character(
        self, user_id: str, draft_id, backstory: str | None = None
    ) -> dict:
        try:
            identifier = UUID(str(draft_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ServiceError(msg="Character draft not found.", code=422) from exc
        draft = await self.draft_repo.get_owned_for_update(
            identifier, coerce_identifier(user_id)
        )
        if draft is None:
            raise ServiceError(msg="Character draft not found.", code=422)
        if draft.saved_character_id is not None:
            character = await self.character_repo.get_one(
                id=draft.saved_character_id, owner_id=coerce_identifier(user_id)
            )
            if character is None:
                raise ServiceError(msg="Character not found.", code=422)
            return self._saved_result(character)
        if backstory is not None and (not backstory.strip() or len(backstory) > 10000):
            raise ServiceError(msg="Backstory text is invalid.", code=422)
        if draft.target_character_id is None:
            await self._enforce_daily_generation_limit(user_id, "save_character")
        data = draft.data or {}
        payload = {
            field: data[field] for field in CHARACTER_DRAFT_FIELDS if field in data
        }
        try:
            validated = CharacterCreateSchema(**payload)
        except ValidationError as exc:
            raise ServiceError(msg=friendly_validation_message(exc), code=422) from exc

        stats = data.get("stats")
        stats_values = _draft_stats_values(stats) if stats else None

        if draft.target_character_id is None:
            character = await self.character_repo.create(
                id=draft.id,
                owner_id=coerce_identifier(user_id),
                **validated.model_dump(),
            )
            needs_recalculation = False
        else:
            character = await self.character_repo.get_one(
                id=draft.target_character_id, owner_id=coerce_identifier(user_id)
            )
            if character is None:
                raise ServiceError(msg="Character not found.", code=422)
            needs_recalculation = any(
                getattr(character, field) != getattr(validated, field)
                for field in ("level", "spec_class", "kind")
            )
            for field, value in validated.model_dump().items():
                setattr(character, field, value)

        stats = await self.stats_repo.get_one(character_id=character.id)
        if stats_values is not None:
            needs_recalculation |= stats is None or any(
                getattr(stats, field) != value for field, value in stats_values.items()
            )
            if stats is None:
                stats = await self.stats_repo.create(
                    character_id=character.id, **stats_values
                )
            else:
                for field, value in stats_values.items():
                    setattr(stats, field, value)
        if needs_recalculation and draft.target_character_id is not None:
            combat = await self.combat_repo.get_one(character_id=character.id)
            if combat is not None:
                recalculate_combat_hit_dice(combat, character, stats)
        if backstory is not None:
            if self.backstory_repo is None:
                raise ServiceError(msg="Backstory saving is unavailable.", code=422)
            saved_backstory = await self.backstory_repo.get_one(
                character_id=character.id
            )
            if saved_backstory is None:
                await self.backstory_repo.create(
                    character_id=character.id, backstory=backstory
                )
            else:
                saved_backstory.backstory = backstory
        draft.saved_character_id = character.id
        draft.data = {}
        try:
            await self.uow.commit()
        except Exception:
            try:
                await self.uow.rollback()
            except Exception:
                logger.exception(
                    "character_save_rollback_failed",
                    user_id=str(user_id),
                    draft_id=str(identifier),
                )
            logger.exception(
                "character_save_commit_failed",
                user_id=str(user_id),
                draft_id=str(identifier),
                character_id=str(character.id),
            )
            raise
        await self.uow.refresh(character)

        await cache.delete_pattern(f"characters:list:{user_id}*")
        if draft.target_character_id is not None:
            await cache.delete_pattern(f"characters:by_id:*:{character.id}")
            await cache.delete_pattern(f"stats:{character.id}")
            await cache.delete_pattern(f"combat:{character.id}")

        return self._saved_result(character)

    async def generate_character(self, user_id: str, draft_id, method: str) -> dict:
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

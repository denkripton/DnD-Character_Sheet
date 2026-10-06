from src.config import settings
from src.infrastructure.redis import cache
from src.modules.ai import AIService
from src.modules.character.backstory.prompt import build_backstory_prompt
from src.modules.character.backstory.schemas import (
    BackstoryCreateSchema,
    BackstoryReadSchema,
)
from src.modules.character.base.enums.generation_limits import GenerationLimits
from src.modules.character.repositories import (
    BackstoryRepository,
    CombatRepository,
    FeatureRepository,
    PersonalityRepository,
    ProficiencyRepository,
    SavingThrowsRepository,
    SkillRepository,
    StatsRepository,
)
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.utils.exceptions import RateLimitExceeded, ServiceError
from src.utils.interfaces.rate_limiter import RateLimiter
from src.utils.unit_of_work import UnitOfWork


class BackstoryService:
    def __init__(
        self,
        ownership_guard: CharacterOwnershipGuard,
        backstory_repository: BackstoryRepository,
        ai_client: AIService,
        stats_repository: StatsRepository,
        combat_repository: CombatRepository,
        personality_repository: PersonalityRepository,
        feature_repository: FeatureRepository,
        skill_repository: SkillRepository,
        proficiency_repository: ProficiencyRepository,
        saving_throws_repository: SavingThrowsRepository,
        unit_of_work: UnitOfWork,
        rate_limiter: RateLimiter,
    ):
        self.ownership = ownership_guard
        self.repo = backstory_repository
        self.ai = ai_client
        self.stats_repo = stats_repository
        self.combat_repo = combat_repository
        self.personality_repo = personality_repository
        self.feature_repo = feature_repository
        self.skill_repo = skill_repository
        self.proficiency_repo = proficiency_repository
        self.saving_throws_repo = saving_throws_repository
        self.uow = unit_of_work
        self.rate_limiter = rate_limiter

    async def _upsert(self, character_id, data: dict):
        obj = await self.repo.get_one(character_id=character_id)
        if obj is not None:
            for key, value in data.items():
                setattr(obj, key, value)
        else:
            obj = await self.repo.create(character_id=character_id, **data)

        await self.uow.commit()
        await self.uow.refresh(obj)
        await cache.delete_pattern(f"backstory:{character_id}")
        return obj

    async def _context(self, character_id):
        context = {}

        stats = await self.stats_repo.get_one(character_id=character_id)
        if stats is not None:
            context["stats"] = stats

        combat = await self.combat_repo.get_one(character_id=character_id)
        if combat is not None:
            context["combat"] = combat

        personality = await self.personality_repo.get_one(
            character_id=character_id
        )
        if personality is not None:
            context["personality"] = personality

        saving_throws = await self.saving_throws_repo.get_one(
            character_id=character_id
        )
        if saving_throws is not None:
            context["saving_throws"] = saving_throws

        features = await self.feature_repo.get_many(character_id=character_id)
        if features:
            context["features"] = features

        skills = await self.skill_repo.get_many(character_id=character_id)
        if skills:
            context["skills"] = skills

        proficiencies = await self.proficiency_repo.get_many(
            character_id=character_id
        )
        if proficiencies:
            context["proficiencies"] = proficiencies

        return context

    async def _enforce_generation_limit(self, user_id) -> None:
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

    async def _prompt_text(self, character, prompt: str | None) -> str:
        context = await self._context(character.id)
        base = build_backstory_prompt(character, context)
        if prompt:
            return f"{base}\nAdditional instructions from the player:\n{prompt}"
        return base

    @staticmethod
    def _validate_text(text: str) -> None:
        if len(text) == 0:
            raise ServiceError(code=422, msg="Empty back story")
        if len(text) >= 1000:
            raise ServiceError(code=422, msg="Back story is too big")

    async def get_backstory(self, user_id, character_id):
        await self.ownership.get_owned(user_id, character_id)
        key = f"backstory:{character_id}"
        cached = await cache.get(key)
        if cached is not None:
            return BackstoryReadSchema(**cached)

        backstory = await self.repo.get_one(character_id=character_id)
        result = (
            BackstoryReadSchema.model_validate(backstory) if backstory is not None else None
        )
        if result is not None:
            await cache.set(key, result.model_dump(mode="json"))
        return result

    async def set_backstory(
        self, user_id, character_id, data: BackstoryCreateSchema
    ):
        await self.ownership.get_owned(user_id, character_id)
        return await self._upsert(
            character_id=character_id,
            data=data.model_dump(mode="json"),
        )

    async def preview_backstory(
        self,
        user_id,
        character_id,
        model: str | None = None,
        provider: str | None = None,
        prompt: str | None = None,
    ) -> str:
        character = await self.ownership.get_owned(user_id, character_id)
        await self._enforce_generation_limit(user_id)
        prompt_text = await self._prompt_text(character, prompt)
        text = await self.ai.generate(prompt_text, model=model, provider=provider)
        self._validate_text(text)
        return text

    async def generate_backstory(
        self,
        user_id,
        character_id,
        model: str | None = None,
        provider: str | None = None,
        prompt: str | None = None,
    ):
        text = await self.preview_backstory(
            user_id, character_id, model=model, provider=provider, prompt=prompt
        )
        return await self._upsert(
            character_id=character_id, data={"backstory": text}
        )

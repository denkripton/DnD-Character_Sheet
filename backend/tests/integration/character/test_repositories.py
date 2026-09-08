import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.databases.sql import Base
from src.modules.auth.models import User
from src.modules.auth.repository import UserRepository
from src.modules.character.models import (
    Character,
    Combat,
    Feature,
    Personality,
    Proficiency,
    SavingThrows,
    Skill,
    Stat,
)
from src.modules.character.repositories import (
    CharacterRepository,
    CombatRepository,
    FeatureRepository,
    PersonalityRepository,
    ProficiencyRepository,
    SavingThrowsRepository,
    SkillRepository,
    StatsRepository,
)

OWNER = uuid.uuid4()
OTHER = uuid.uuid4()


def _build_session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    maker = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    async def open_session():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return maker()

    return open_session, engine


def _run(scenario):
    open_session, engine = _build_session()

    async def wrapper():
        session = await open_session()
        try:
            return await scenario(session)
        finally:
            await session.close()

    try:
        asyncio.run(wrapper())
    finally:
        asyncio.run(engine.dispose())


def test_repositories_bound_to_models():
    assert CharacterRepository.model is Character
    assert StatsRepository.model is Stat
    assert CombatRepository.model is Combat
    assert SavingThrowsRepository.model is SavingThrows
    assert SkillRepository.model is Skill
    assert ProficiencyRepository.model is Proficiency
    assert FeatureRepository.model is Feature
    assert PersonalityRepository.model is Personality
    assert UserRepository.model is User


def test_character_repository_create_and_get_by_id():
    def scenario(session):
        repo = CharacterRepository(session)

        async def run():
            created = await repo.create(
                name="Grog",
                spec_class="Barbarian",
                kind="Human",
                owner_id=OWNER,
            )
            await session.commit()
            found = await repo.get_by_id(created.id)
            assert found is not None
            assert found.id == created.id
            assert found.spec_class == "Barbarian"
            assert found.level == 1

        return run()

    _run(scenario)


def test_get_one_filters_and_skips_none():
    def scenario(session):
        repo = CharacterRepository(session)

        async def run():
            first = await repo.create(
                name="Grog", spec_class="Barbarian", kind="Human", owner_id=OWNER
            )
            second = await repo.create(
                name="Tina", spec_class="Wizard", kind="Elf", owner_id=OWNER
            )
            await session.commit()

            assert (await repo.get_one(id=first.id, owner_id=OWNER)).id == first.id
            assert (await repo.get_one(id=second.id, owner_id=OWNER)).id == second.id
            assert (
                await repo.get_one(id=first.id, owner_id=OTHER)
            ) is None
            assert (await repo.get_one(id=first.id, owner_id=None)).id == first.id
            assert (await repo.get_one(id=uuid.uuid4())) is None

        return run()

    _run(scenario)


def test_get_many_skip_and_limit():
    def scenario(session):
        repo = CharacterRepository(session)

        async def run():
            for index in range(5):
                await repo.create(
                    name=f"Hero {index}",
                    spec_class="Fighter",
                    kind="Human",
                    owner_id=OWNER,
                )
            await session.commit()

            assert len(await repo.get_many(owner_id=OWNER)) == 5
            assert len(await repo.get_many(owner_id=OTHER)) == 0
            assert len(await repo.get_many(skip=1, limit=2, owner_id=OWNER)) == 2

        return run()

    _run(scenario)


def test_delete_obj_removes_row():
    def scenario(session):
        repo = CharacterRepository(session)

        async def run():
            created = await repo.create(
                name="Grog", spec_class="Barbarian", kind="Human", owner_id=OWNER
            )
            await session.commit()
            await repo.delete_obj(created.id)
            await session.commit()
            assert await repo.get_by_id(created.id) is None

        return run()

    _run(scenario)


def test_user_repository_get_by_email():
    def scenario(session):
        repo = UserRepository(session)

        async def run():
            await repo.create(
                username="john", email="johndoe@gmail.com", password=b"hashed"
            )
            await session.commit()

            found = await repo.get_by_email("johndoe@gmail.com")
            assert found is not None
            assert found.username == "john"
            assert await repo.get_by_email("missing@x.y") is None

        return run()

    _run(scenario)


def test_stats_repository_create_and_fetch():
    def scenario(session):
        char_repo = CharacterRepository(session)
        stats_repo = StatsRepository(session)

        async def run():
            character = await char_repo.create(
                name="Grog", spec_class="Barbarian", kind="Human", owner_id=OWNER
            )
            await session.commit()

            await stats_repo.create(
                strength=15,
                dexterity=14,
                constitution=15,
                intelligence=8,
                wisdom=10,
                charisma=8,
                character_id=character.id,
            )
            await session.commit()

            stats = await stats_repo.get_one(character_id=character.id)
            assert stats is not None
            assert stats.strength == 15
            assert stats.constitution == 15

        return run()

    _run(scenario)


def test_combat_repository_scoped_by_character():
    def scenario(session):
        char_repo = CharacterRepository(session)
        combat_repo = CombatRepository(session)

        async def run():
            character = await char_repo.create(
                name="Grog", spec_class="Barbarian", kind="Human", owner_id=OWNER
            )
            await session.commit()

            await combat_repo.create(
                character_id=character.id,
                max_hp=14,
                armor_class=14,
                hit_dice_total="1d12",
                hit_dice_remaining=1,
            )
            await session.commit()

            combat = await combat_repo.get_one(character_id=character.id)
            assert combat is not None
            assert combat.max_hp == 14
            assert combat.hit_dice_total == "1d12"

        return run()

    _run(scenario)


def test_skill_repository_filters_by_character():
    def scenario(session):
        char_repo = CharacterRepository(session)
        skill_repo = SkillRepository(session)

        async def run():
            first_char = await char_repo.create(
                name="Grog", spec_class="Barbarian", kind="Human", owner_id=OWNER
            )
            second_char = await char_repo.create(
                name="Tina", spec_class="Wizard", kind="Elf", owner_id=OWNER
            )
            await session.commit()

            await skill_repo.create(
                name="Athletics", ability="strength", character_id=first_char.id
            )
            await skill_repo.create(
                name="Arcana", ability="intelligence", character_id=second_char.id
            )
            await session.commit()

            skills = await skill_repo.get_many(character_id=first_char.id)
            assert len(skills) == 1
            assert skills[0].name == "Athletics"
            assert len(await skill_repo.get_many(character_id=second_char.id)) == 1

        return run()

    _run(scenario)


def test_one_to_one_blocks_create_and_fetch():
    def scenario(session):
        char_repo = CharacterRepository(session)
        saving_throws_repo = SavingThrowsRepository(session)
        personality_repo = PersonalityRepository(session)

        async def run():
            character = await char_repo.create(
                name="Grog", spec_class="Barbarian", kind="Human", owner_id=OWNER
            )
            await session.commit()

            await saving_throws_repo.create(
                strength=True,
                dexterity=False,
                constitution=True,
                intelligence=False,
                wisdom=False,
                charisma=False,
                character_id=character.id,
            )
            await personality_repo.create(
                personality_traits="Brave",
                ideals="Strength",
                bonds="Clan",
                flaws="Rage",
                character_id=character.id,
            )
            await session.commit()

            saves = await saving_throws_repo.get_one(character_id=character.id)
            assert saves is not None
            assert saves.strength is True
            assert saves.dexterity is False

            personality = await personality_repo.get_one(character_id=character.id)
            assert personality is not None
            assert personality.personality_traits == "Brave"
            assert personality.flaws == "Rage"

        return run()

    _run(scenario)


def test_proficiency_and_feature_repositories():
    def scenario(session):
        char_repo = CharacterRepository(session)
        proficiency_repo = ProficiencyRepository(session)
        feature_repo = FeatureRepository(session)

        async def run():
            character = await char_repo.create(
                name="Grog", spec_class="Barbarian", kind="Human", owner_id=OWNER
            )
            await session.commit()

            await proficiency_repo.create(
                category="weapon", name="Battleaxe", character_id=character.id
            )
            await feature_repo.create(
                name="Rage",
                description="Enter a rage",
                character_id=character.id,
            )
            await session.commit()

            proficiencies = await proficiency_repo.get_many(character_id=character.id)
            features = await feature_repo.get_many(character_id=character.id)
            assert len(proficiencies) == 1
            assert proficiencies[0].category == "weapon"
            assert len(features) == 1
            assert features[0].name == "Rage"

        return run()

    _run(scenario)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("repository tests passed")
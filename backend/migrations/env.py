from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from src.databases.sql import Base
from src.config import settings
from src.modules.auth.models import User
from src.modules.character.models.character import Character
from src.modules.character.models.stats import Stat
from src.modules.character.models.combat import Combat
from src.modules.character.models.saving_throws import SavingThrows
from src.modules.character.models.skill import Skill
from src.modules.character.models.proficiency import Proficiency
from src.modules.character.models.feature import Feature
from src.modules.character.models.personality import Personality
from src.modules.character.models.backstory import Backstory

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.DB_URL + "?async_fallback=True")

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
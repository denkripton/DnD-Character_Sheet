from collections.abc import Sequence

from alembic import op

revision: str = 'ef8c5a2b4d91'
down_revision: str | Sequence[str] | None = '0b2ebd5a7362'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CHILD_TABLES = [
    'stats',
    'combat',
    'saving_throws',
    'skills',
    'proficiencies',
    'features',
    'personality',
    'backstories',
]


def _fk_name(table: str) -> str:
    return f"{table}_character_id_fkey"


def upgrade() -> None:
    # Remove duplicate stats rows created by the pre-constraint race so the
    # new unique constraint can be applied (keep the earliest row per character).
    op.execute(
        "DELETE FROM stats WHERE id NOT IN "
        "(SELECT MIN(id) FROM stats GROUP BY character_id)"
    )

    # stats.character_id was the only 1:1 FK without a unique constraint.
    op.execute(
        "ALTER TABLE stats ADD CONSTRAINT uq_stats_character_id "
        "UNIQUE (character_id)"
    )

    # Rebuild every child FK with ON DELETE CASCADE so a single DELETE on
    # characters cleans up all children instead of the ORM loading them.
    for table in CHILD_TABLES:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {_fk_name(table)}")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {_fk_name(table)} "
            f"FOREIGN KEY (character_id) REFERENCES characters(id) "
            f"ON DELETE CASCADE"
        )


def downgrade() -> None:
    for table in CHILD_TABLES:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {_fk_name(table)}")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {_fk_name(table)} "
            f"FOREIGN KEY (character_id) REFERENCES characters(id)"
        )

    op.execute("ALTER TABLE stats DROP CONSTRAINT IF EXISTS uq_stats_character_id")
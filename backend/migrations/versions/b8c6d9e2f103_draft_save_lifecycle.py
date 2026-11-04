from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c6d9e2f103"
down_revision: str | Sequence[str] | None = "e5a8c1d7f3b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("character_drafts", sa.Column("target_character_id", sa.UUID(), nullable=True))
    op.add_column("character_drafts", sa.Column("saved_character_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_character_drafts_target_character_id_characters",
        "character_drafts", "characters", ["target_character_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_character_drafts_target_character_id_characters", "character_drafts", type_="foreignkey"
    )
    op.drop_column("character_drafts", "saved_character_id")
    op.drop_column("character_drafts", "target_character_id")

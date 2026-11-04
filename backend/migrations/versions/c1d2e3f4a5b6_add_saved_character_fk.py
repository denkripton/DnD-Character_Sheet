from collections.abc import Sequence

from alembic import op


revision: str = "c1d2e3f4a5b6"
down_revision: str | Sequence[str] | None = "b8c6d9e2f103"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_character_drafts_saved_character_id_characters",
        "character_drafts",
        "characters",
        ["saved_character_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_character_drafts_saved_character_id_characters",
        "character_drafts",
        type_="foreignkey",
    )

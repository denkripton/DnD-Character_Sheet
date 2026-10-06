from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'e5a8c1d7f3b2'
down_revision: str | Sequence[str] | None = 'f4a9c3e2b7d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'character_drafts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('character_drafts')

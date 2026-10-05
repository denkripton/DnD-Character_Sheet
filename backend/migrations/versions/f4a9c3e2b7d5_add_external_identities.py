from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f4a9c3e2b7d5'
down_revision: str | Sequence[str] | None = 'ef8c5a2b4d91'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'external_identities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('provider_user_id', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'provider',
            'provider_user_id',
            name='uq_external_identities_provider_user',
        ),
    )


def downgrade() -> None:
    op.drop_table('external_identities')
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0b2ebd5a7362'
down_revision: Union[str, Sequence[str], None] = 'd9e4f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'backstories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('backstory', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('character_id'),
    )


def downgrade() -> None:
    op.drop_table('backstories')
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd9e4f1a2b3c4'
down_revision: Union[str, Sequence[str], None] = 'c7f2a3b9d001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'characters',
        sa.Column('level', sa.Integer(), server_default='1', nullable=False),
    )

    op.add_column(
        'combat',
        sa.Column('bonus_hp', sa.Integer(), server_default='0', nullable=False),
    )

    for stat in ('strength', 'dexterity', 'constitution',
                 'intelligence', 'wisdom', 'charisma'):
        op.create_check_constraint(
            f'ck_{stat}_range',
            'stats',
            f'"{stat}" >= 3 AND "{stat}" <= 20',
        )


def downgrade() -> None:
    for stat in ('strength', 'dexterity', 'constitution',
                 'intelligence', 'wisdom', 'charisma'):
        op.drop_constraint(f'ck_{stat}_range', 'stats', type_='check')

    op.drop_column('combat', 'bonus_hp')
    op.drop_column('characters', 'level')
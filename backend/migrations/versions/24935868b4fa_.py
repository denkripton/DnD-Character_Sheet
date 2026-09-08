from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '24935868b4fa'
down_revision: Union[str, Sequence[str], None] = 'a41f4945ff83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('stats', 'strenght', new_column_name='strength')


def downgrade() -> None:
    op.alter_column('stats', 'strength', new_column_name='strenght')
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a41f4945ff83'
down_revision: Union[str, Sequence[str], None] = 'fcca43291db6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
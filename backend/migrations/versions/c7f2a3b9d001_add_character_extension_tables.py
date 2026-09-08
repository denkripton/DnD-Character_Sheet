from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7f2a3b9d001'
down_revision: Union[str, Sequence[str], None] = '73d12c63a500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('characters', sa.Column('alignment', sa.String(length=30), nullable=True))
    op.add_column('characters', sa.Column('background', sa.String(length=50), nullable=True))
    op.add_column('characters', sa.Column('experience_points', sa.Integer(), nullable=True))

    op.create_table(
        'combat',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('current_hp', sa.Integer(), nullable=False),
        sa.Column('max_hp', sa.Integer(), nullable=False),
        sa.Column('temp_hp', sa.Integer(), nullable=False),
        sa.Column('armor_class', sa.Integer(), nullable=False),
        sa.Column('initiative', sa.Integer(), nullable=False),
        sa.Column('speed', sa.Integer(), nullable=False),
        sa.Column('proficiency_bonus', sa.Integer(), nullable=False),
        sa.Column('hit_dice_total', sa.String(length=20), nullable=False),
        sa.Column('hit_dice_remaining', sa.Integer(), nullable=False),
        sa.Column('inspiration', sa.Boolean(), nullable=False),
        sa.Column('death_save_successes', sa.Integer(), nullable=False),
        sa.Column('death_save_failures', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('character_id'),
    )

    op.create_table(
        'saving_throws',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('strength', sa.Boolean(), nullable=False),
        sa.Column('dexterity', sa.Boolean(), nullable=False),
        sa.Column('constitution', sa.Boolean(), nullable=False),
        sa.Column('intelligence', sa.Boolean(), nullable=False),
        sa.Column('wisdom', sa.Boolean(), nullable=False),
        sa.Column('charisma', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('character_id'),
    )

    op.create_table(
        'skills',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('ability', sa.String(length=20), nullable=False),
        sa.Column('proficiency', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'proficiencies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'features',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'personality',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('personality_traits', sa.Text(), nullable=False),
        sa.Column('ideals', sa.Text(), nullable=False),
        sa.Column('bonds', sa.Text(), nullable=False),
        sa.Column('flaws', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('character_id'),
    )


def downgrade() -> None:
    op.drop_table('personality')
    op.drop_table('features')
    op.drop_table('proficiencies')
    op.drop_table('skills')
    op.drop_table('saving_throws')
    op.drop_table('combat')

    op.drop_column('characters', 'experience_points')
    op.drop_column('characters', 'background')
    op.drop_column('characters', 'alignment')
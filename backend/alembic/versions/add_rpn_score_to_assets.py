"""Add RPN score to assets for FMEA

Revision ID: add_rpn_score_to_assets
Revises: initial_migration
Create Date: 2025-12-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_rpn_score_to_assets'
down_revision: Union[str, None] = 'initial_migration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add RPN score column to assets table."""
    op.add_column('assets', sa.Column('rpn_score', sa.Integer(), nullable=True))
    op.create_index('ix_assets_rpn_score', 'assets', ['rpn_score'])


def downgrade() -> None:
    """Remove RPN score column from assets table."""
    op.drop_index('ix_assets_rpn_score', 'assets')
    op.drop_column('assets', 'rpn_score')

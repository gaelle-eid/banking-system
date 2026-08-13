"""add source to transactions for realistic deposit funding sources

Revision ID: a6464cf7e1fb
Revises: bac98dedccae
Create Date: 2026-08-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6464cf7e1fb'
down_revision: Union[str, Sequence[str], None] = 'bac98dedccae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'transactions',
        sa.Column('source', sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('transactions', 'source')
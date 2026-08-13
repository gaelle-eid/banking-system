"""add frozen to cards for instant reversible lock

Revision ID: 9c4a356e800f
Revises: 590988faccca
Create Date: 2026-08-13 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4a356e800f'
down_revision: Union[str, Sequence[str], None] = '590988faccca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'cards',
        sa.Column('frozen', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('cards', 'frozen')
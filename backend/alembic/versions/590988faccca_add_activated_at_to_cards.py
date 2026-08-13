"""add activated_at to cards for client-side activation

Revision ID: 590988faccca
Revises: 76d1ec569d8e
Create Date: 2026-08-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '590988faccca'
down_revision: Union[str, Sequence[str], None] = '76d1ec569d8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'cards',
        sa.Column('activated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('cards', 'activated_at')
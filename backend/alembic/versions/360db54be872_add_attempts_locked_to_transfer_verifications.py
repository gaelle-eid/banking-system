"""add attempts and locked to transfer_verifications for OTP lockout

Revision ID: 360db54be872
Revises: 9c4a356e800f
Create Date: 2026-08-13 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '360db54be872'
down_revision: Union[str, Sequence[str], None] = '9c4a356e800f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'transfer_verifications',
        sa.Column('attempts', sa.Numeric(), nullable=False, server_default='0'),
    )
    op.add_column(
        'transfer_verifications',
        sa.Column('locked', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('transfer_verifications', 'locked')
    op.drop_column('transfer_verifications', 'attempts')
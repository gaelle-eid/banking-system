"""add tier to cards

Revision ID: 63ce47d2e440
Revises: 0a2099abcbad
Create Date: 2026-08-07 15:11:18.476274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63ce47d2e440'
down_revision: Union[str, Sequence[str], None] = '0a2099abcbad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    cardtier_enum = sa.Enum('standard', 'cashback', 'travel', 'premium', name='cardtier')
    cardtier_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('cards', sa.Column('tier', cardtier_enum, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('cards', 'tier')
    sa.Enum(name='cardtier').drop(op.get_bind(), checkfirst=True)
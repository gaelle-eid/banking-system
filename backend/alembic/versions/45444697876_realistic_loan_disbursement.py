"""add purpose, disbursement account, and disbursed_at to loans; rate now set by bank

Revision ID: 745444697876
Revises: 360db54be872
Create Date: 2026-08-13 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '745444697876'
down_revision: Union[str, Sequence[str], None] = '360db54be872'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('loans', 'interest_rate', nullable=True)
    op.add_column('loans', sa.Column('purpose', sa.String(), nullable=True))
    op.add_column('loans', sa.Column('disbursement_account_id', UUID(as_uuid=False), sa.ForeignKey('accounts.id'), nullable=True))
    op.add_column('loans', sa.Column('disbursed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('loans', 'disbursed_at')
    op.drop_column('loans', 'disbursement_account_id')
    op.drop_column('loans', 'purpose')
    op.alter_column('loans', 'interest_rate', nullable=False)
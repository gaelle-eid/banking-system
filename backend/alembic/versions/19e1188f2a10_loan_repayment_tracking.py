"""add loan repayment tracking fields

Revision ID: 19e1188f2a10
Revises: 745444697876
Create Date: 2026-08-13 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19e1188f2a10'
down_revision: Union[str, Sequence[str], None] = '745444697876'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('loans', sa.Column('total_repayment', sa.Numeric(14, 2), nullable=True))
    op.add_column('loans', sa.Column('monthly_payment', sa.Numeric(14, 2), nullable=True))
    op.add_column('loans', sa.Column('remaining_balance', sa.Numeric(14, 2), nullable=True))
    op.add_column('loans', sa.Column('next_payment_due', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('loans', 'next_payment_due')
    op.drop_column('loans', 'remaining_balance')
    op.drop_column('loans', 'monthly_payment')
    op.drop_column('loans', 'total_repayment')
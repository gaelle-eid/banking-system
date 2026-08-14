"""make statements real snapshots with balances and transaction history

Revision ID: aa43b9cf9bb8
Revises: 19e1188f2a10
Create Date: 2026-08-13 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa43b9cf9bb8'
down_revision: Union[str, Sequence[str], None] = '19e1188f2a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('statements', sa.Column('opening_balance', sa.Numeric(14, 2), nullable=True))
    op.add_column('statements', sa.Column('closing_balance', sa.Numeric(14, 2), nullable=True))
    op.add_column('statements', sa.Column('total_deposits', sa.Numeric(14, 2), nullable=True))
    op.add_column('statements', sa.Column('total_withdrawals', sa.Numeric(14, 2), nullable=True))
    op.add_column('statements', sa.Column('currency', sa.String(), nullable=True))
    op.add_column('statements', sa.Column('transactions_snapshot', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('statements', 'transactions_snapshot')
    op.drop_column('statements', 'currency')
    op.drop_column('statements', 'total_withdrawals')
    op.drop_column('statements', 'total_deposits')
    op.drop_column('statements', 'closing_balance')
    op.drop_column('statements', 'opening_balance')
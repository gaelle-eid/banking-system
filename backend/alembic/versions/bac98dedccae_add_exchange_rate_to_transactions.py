"""add exchange_rate to transactions for multi-currency transfers

Revision ID: bac98dedccae
Revises: 71b0456e7113
Create Date: 2026-08-12 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bac98dedccae'
down_revision: Union[str, Sequence[str], None] = '71b0456e7113'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'transactions',
        sa.Column('exchange_rate', sa.Numeric(18, 8), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('transactions', 'exchange_rate')
"""add transaction categories

Revision ID: d9b16d2b9387
Revises: aa43b9cf9bb8
Create Date: 2026-08-14 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9b16d2b9387'
down_revision: Union[str, Sequence[str], None] = 'aa43b9cf9bb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE transactioncategory AS ENUM (
                'dining', 'groceries', 'travel', 'entertainment', 'bills_utilities',
                'shopping', 'healthcare', 'transfer_to_person', 'cash_withdrawal',
                'income', 'loan_repayment', 'savings', 'other'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS category transactioncategory;")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE transactions DROP COLUMN IF EXISTS category;")
    op.execute("DROP TYPE IF EXISTS transactioncategory;")
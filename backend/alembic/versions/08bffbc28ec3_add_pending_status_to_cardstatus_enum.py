"""add pending status to CardStatus enum

Revision ID: 08bffbc28ec3
Revises: d8a977452220
Create Date: 2026-08-04 16:41:17.596495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08bffbc28ec3'
down_revision: Union[str, Sequence[str], None] = 'd8a977452220'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE cardstatus ADD VALUE IF NOT EXISTS 'pending' BEFORE 'active'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres doesn't support removing enum values directly.
    # Would require recreating the type; skipping for this project's scope.
    pass
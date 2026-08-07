"""add registration_status to users

Revision ID: fb33a4f484b8
Revises: daac15bf9b0d
Create Date: 2026-08-07 15:57:07.945496

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb33a4f484b8'
down_revision: Union[str, Sequence[str], None] = 'daac15bf9b0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    registration_status_enum = sa.Enum('pending_review', 'approved', 'rejected', name='registrationstatus')
    registration_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'users',
        sa.Column('registration_status', registration_status_enum, nullable=False, server_default='approved'),
    )
    op.alter_column('users', 'registration_status', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'registration_status')
    sa.Enum(name='registrationstatus').drop(op.get_bind(), checkfirst=True)
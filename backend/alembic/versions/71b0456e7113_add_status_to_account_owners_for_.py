"""add status to account_owners for invite/accept flow

Revision ID: 71b0456e7113
Revises: 6f6d4fc99753
Create Date: 2026-08-11 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '71b0456e7113'
down_revision: Union[str, Sequence[str], None] = '6f6d4fc99753'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    joint_owner_status_enum = sa.Enum('pending', 'accepted', 'declined', name='jointownerstatus')
    joint_owner_status_enum.create(op.get_bind(), checkfirst=True)

    # Existing joint owners (added before this invite flow existed) are
    # treated as already-accepted, so this doesn't retroactively revoke
    # access anyone already had.
    op.add_column(
        'account_owners',
        sa.Column('status', joint_owner_status_enum, nullable=False, server_default='accepted'),
    )
    op.alter_column('account_owners', 'status', server_default=None)

    op.add_column(
        'account_owners',
        sa.Column('invited_by', UUID(as_uuid=False), sa.ForeignKey('users.id'), nullable=True),
    )
    op.add_column(
        'account_owners',
        sa.Column('responded_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('account_owners', 'responded_at')
    op.drop_column('account_owners', 'invited_by')
    op.drop_column('account_owners', 'status')
    sa.Enum(name='jointownerstatus').drop(op.get_bind(), checkfirst=True)
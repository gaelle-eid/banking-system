"""create funding_sources table for micro-deposit verified deposits

Revision ID: 04acd4a37e4c
Revises: a6464cf7e1fb
Create Date: 2026-08-12 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '04acd4a37e4c'
down_revision: Union[str, Sequence[str], None] = 'a6464cf7e1fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    funding_source_status_enum = sa.Enum('pending_verification', 'verified', 'failed', name='fundingsourcestatus')
    funding_source_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'funding_sources',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('bank_name', sa.String(), nullable=False),
        sa.Column('masked_account_number', sa.String(), nullable=False),
        sa.Column('status', funding_source_status_enum, nullable=False, server_default='pending_verification'),
        sa.Column('micro_deposit_1', sa.Numeric(4, 2), nullable=True),
        sa.Column('micro_deposit_2', sa.Numeric(4, 2), nullable=True),
        sa.Column('verification_attempts', sa.Numeric(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('funding_sources')
    sa.Enum(name='fundingsourcestatus').drop(op.get_bind(), checkfirst=True)
"""create funding_sources table for micro-deposit verified deposits

Revision ID: 04acd4a37e4c
Revises: a6464cf7e1fb
Create Date: 2026-08-12 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04acd4a37e4c'
down_revision: Union[str, Sequence[str], None] = 'a6464cf7e1fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Raw SQL throughout, sidestepping SQLAlchemy's automatic enum-type
    # creation (which double-creates the type when a column-level Enum is
    # combined with an explicitly pre-created one). The DO block makes type
    # creation idempotent regardless of what state the DB is already in.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE fundingsourcestatus AS ENUM ('pending_verification', 'verified', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS funding_sources (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id),
            bank_name VARCHAR NOT NULL,
            masked_account_number VARCHAR NOT NULL,
            status fundingsourcestatus NOT NULL DEFAULT 'pending_verification',
            micro_deposit_1 NUMERIC(4,2),
            micro_deposit_2 NUMERIC(4,2),
            verification_attempts NUMERIC NOT NULL DEFAULT 0,
            created_at TIMESTAMP,
            verified_at TIMESTAMP
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS funding_sources;")
    op.execute("DROP TYPE IF EXISTS fundingsourcestatus;")
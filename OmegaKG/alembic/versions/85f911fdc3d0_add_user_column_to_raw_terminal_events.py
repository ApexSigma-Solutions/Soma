"""add user column to raw_terminal_events

Revision ID: 85f911fdc3d0
Revises: 83b048ac57c5
Create Date: 2026-01-13 18:18:38.534786

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "85f911fdc3d0"
down_revision = "83b048ac57c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "raw_terminal_events", sa.Column("user", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("raw_terminal_events", "user")

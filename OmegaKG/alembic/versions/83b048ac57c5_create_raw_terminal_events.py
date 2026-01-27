"""create_raw_terminal_events

Revision ID: 83b048ac57c5
Revises: 9ee9fe3ca708
Create Date: 2026-01-13 16:05:32.525700

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "83b048ac57c5"
down_revision = "9ee9fe3ca708"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_terminal_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("cwd", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("host", sa.String(length=255), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column(
            "captured_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "processing_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_index(
        "idx_raw_terminal_events_processed",
        "raw_terminal_events",
        ["processed"],
        postgresql_where=sa.text("processed = FALSE"),
    )
    op.create_index(
        "idx_raw_terminal_events_captured_at", "raw_terminal_events", ["captured_at"]
    )
    op.create_index(
        "idx_raw_terminal_events_session_id", "raw_terminal_events", ["session_id"]
    )


def downgrade() -> None:
    op.drop_table("raw_terminal_events")

"""create_raw_linear_events_table

Revision ID: 001_create_raw_linear_events
Revises:
Create Date: 2026-01-09

This migration creates the raw_linear_events table for Linear webhook storage.
This is the base migration that other migrations depend on.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "000_create_base_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the raw_linear_events table."""
    op.create_table(
        "raw_linear_events",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column(
            "signature",
            sa.String(),
            nullable=False,
            comment="Linear webhook signature for verification",
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
            comment="Server receipt timestamp",
        ),
        sa.Column(
            "external_timestamp",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp from Linear payload data.createdAt",
        ),
        sa.Column(
            "event_type",
            sa.String(),
            index=True,
            nullable=True,
            comment="Event type (issue.created, issue.updated, etc.)",
        ),
        sa.Column(
            "action",
            sa.String(),
            nullable=True,
            comment="Action that triggered the webhook",
        ),
        sa.Column(
            "headers",
            JSONB(),
            nullable=False,
            comment="HTTP headers from webhook",
        ),
        sa.Column(
            "body",
            JSONB(),
            nullable=False,
            comment="Raw JSON payload from Linear",
        ),
        sa.Column(
            "processed",
            sa.Boolean(),
            server_default="false",
            nullable=True,
            comment="Event processing status",
        ),
        sa.Column(
            "error_log",
            sa.String(),
            nullable=True,
            comment="Processing error details if any",
        ),
        sa.PrimaryKeyConstraint("id", name="raw_linear_events_pkey"),
        comment="Raw Linear webhook events for processing",
    )

    # Create composite index for efficient event processing queries
    op.create_index(
        "ix_raw_linear_events_processed_received_at",
        "raw_linear_events",
        ["processed", "received_at"],
    )


def downgrade() -> None:
    """Drop the raw_linear_events table."""
    op.drop_index(
        "ix_raw_linear_events_processed_received_at", table_name="raw_linear_events"
    )
    op.drop_table("raw_linear_events")

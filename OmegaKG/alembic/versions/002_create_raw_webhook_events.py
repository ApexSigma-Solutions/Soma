"""Create raw_webhook_events table for generic webhook ingestion

Revision ID: 003_create_raw_webhook_events
Revises: 002_vector_id_to_string
Create Date: 2025-12-25 00:00:00.000000

Phase 1 (TN-101): RawIngestion Models
Purpose: Decouple ingestion from processing to prevent data loss and enable replayability.

Schema Rationale:
- source: Identifies webhook origin (linear, github, etc.) for routing
- processed_status: Enables reliable at-least-once processing with retry
- headers: Stores original HTTP headers for signature verification and debugging
- payload: Stores raw JSON for replayability if processing logic fails
- event_type: Optimized index for filtering specific event types
- received_at: Server-side timestamp for audit trail
- error_log: Captures processing failures for troubleshooting

Deployment Notes:
- JSONB columns enable flexible schema without migrations
- Indexes on source and event_type for efficient processor polling
- processed_status enables "write fast, process later" pattern
"""

from alembic import op
import sqlalchemy as sa

revision = "003_create_raw_webhook_events"
down_revision = "002_vector_id_to_string"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create the raw_webhook_events table for generic webhook ingestion.

    Stores webhook payloads exactly as received before any processing,
    enabling safe event replay and preventing data loss.
    """
    op.create_table(
        "raw_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column(
            "source",
            sa.String(),
            nullable=False,
            comment="Webhook source (linear, github, etc.)",
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            comment="Server receipt timestamp",
        ),
        sa.Column(
            "processed_status",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Event processing status",
        ),
        sa.Column(
            "headers",
            sa.JSON(),
            nullable=False,
            comment="HTTP headers from webhook",
        ),
        sa.Column(
            "payload",
            sa.JSON(),
            nullable=False,
            comment="Raw JSON payload",
        ),
        sa.Column(
            "event_type",
            sa.String(),
            nullable=True,
            comment="Event type (issue.created, etc.)",
        ),
        sa.Column(
            "error_log",
            sa.String(),
            nullable=True,
            comment="Processing error details if any",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Raw webhook event storage for decoupled ingestion",
    )

    op.create_index(
        "ix_raw_webhook_events_source",
        "raw_webhook_events",
        ["source"],
    )

    op.create_index(
        "ix_raw_webhook_events_event_type",
        "raw_webhook_events",
        ["event_type"],
    )

    op.create_index(
        "ix_raw_webhook_events_processed_status",
        "raw_webhook_events",
        ["processed_status"],
    )


def downgrade() -> None:
    """
    Remove the raw_webhook_events table and all indexes.
    """
    op.drop_table("raw_webhook_events")

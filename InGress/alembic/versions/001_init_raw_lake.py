"""001_init_raw_lake - Fresh Alembic migration for soma_sensory_lake.

Revision ID: 001_init_raw_lake
Revises: -
Create Date: 2026-01-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_init_raw_lake"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create raw_lake table with DLQ columns."""
    op.create_table(
        "raw_lake",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("source", sa.String(64), nullable=False, comment="Origin: obsidian, github, chrome, terminal"),
        sa.Column("event_type", sa.String(128), nullable=False, comment="Type: file_mod, push, web_capture"),
        sa.Column("payload", postgresql.JSONB, nullable=False, comment="Raw signal data"),
        sa.Column("client_ip", sa.String(45), nullable=True, comment="Client IP (IPv4/IPv6)"),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "processed",
            sa.Boolean(),
            server_default=sa.text("FALSE"),
            nullable=False,
            comment="Stomach digestion flag",
        ),
        # DLQ Columns
        sa.Column(
            "failed",
            sa.Boolean(),
            server_default=sa.text("FALSE"),
            nullable=False,
            comment="Dead Letter Queue flag",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="Digestion retry attempts",
        ),
        sa.Column("last_error", sa.Text(), nullable=True, comment="Last failure reason"),
    )

    # Partial index for efficient polling (unprocessed, non-failed records)
    op.create_index(
        "idx_raw_lake_unprocessed",
        "raw_lake",
        ["ingested_at"],
        postgresql_where=sa.text("processed = FALSE AND failed = FALSE"),
    )

    # Index for DLQ monitoring
    op.create_index(
        "idx_raw_lake_dlq",
        "raw_lake",
        ["ingested_at"],
        postgresql_where=sa.text("failed = TRUE"),
    )


def downgrade() -> None:
    """Drop raw_lake table."""
    op.drop_index("idx_raw_lake_dlq", table_name="raw_lake")
    op.drop_index("idx_raw_lake_unprocessed", table_name="raw_lake")
    op.drop_table("raw_lake")

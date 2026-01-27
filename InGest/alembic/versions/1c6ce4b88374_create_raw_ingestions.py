"""create_raw_ingestions

Revision ID: 1c6ce4b88374
Revises:
Create Date: 2026-01-13 14:56:54.306298

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c6ce4b88374"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create raw_ingestions table for durable data lake persistence."""
    op.create_table(
        "raw_ingestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ingestion_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("raw_payload", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("file_data", sa.LargeBinary, nullable=True),
        sa.Column("raw_metadata", sa.dialects.postgresql.JSONB, nullable=True),
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

    # Create indexes for worker polling efficiency
    op.create_index(
        "idx_raw_ingestions_processed",
        "raw_ingestions",
        ["processed"],
        postgresql_where=sa.text("processed = FALSE"),
    )
    op.create_index("idx_raw_ingestions_captured_at", "raw_ingestions", ["captured_at"])
    op.create_index("idx_raw_ingestions_source_type", "raw_ingestions", ["source_type"])
    op.create_index(
        "idx_raw_ingestions_ingestion_id",
        "raw_ingestions",
        ["ingestion_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop raw_ingestions table."""
    op.drop_index("idx_raw_ingestions_ingestion_id", table_name="raw_ingestions")
    op.drop_index("idx_raw_ingestions_source_type", table_name="raw_ingestions")
    op.drop_index("idx_raw_ingestions_captured_at", table_name="raw_ingestions")
    op.drop_index("idx_raw_ingestions_processed", table_name="raw_ingestions")
    op.drop_table("raw_ingestions")

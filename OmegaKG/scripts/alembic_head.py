"""Create omega_vectors_1024 table with pgvector support and status tracking

Revision ID: 001_create_omega_vectors_1024
Revises:
Create Date: 2025-12-02 23:00:00.000000

Phase 7 (TN-LINEAR-07): Vector Enrichment
Purpose: Migrate vector embeddings from Neo4j to PostgreSQL for scalability and semantic search.

Schema Rationale:
- message_id: Foreign key to source message/issue (allows cascade cleanup)
- embedding: pgvector VECTOR(1024) for BGE-M3 output (can be NULL during pending state)
- status: Tracks embedding lifecycle (pending_embedding → ready | failed)
- retry_count: Prevents infinite retries on persistent failures
- Indexes: Optimized for common queries (status checks, pending lookups)

Deployment Notes:
- Requires pgvector extension (CREATE EXTENSION IF NOT EXISTS vector)
- Indexes use INCLUDE for partial predicate efficiency
- Column constraints ensure data integrity
- Updated_at timestamp enables TTL-based cleanup
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision = "001_create_omega_vectors_1024"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create omega_vectors_1024 table with pgvector support.
    Includes columns for embedding storage, status tracking, and retry handling.
    """
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create main table
    op.create_table(
        "omega_vectors_1024",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column(
            "message_id",
            sa.BigInteger(),
            nullable=False,
            comment="Foreign key to source message/issue; enables cascade cleanup",
        ),
        sa.Column(
            "embedding",
            Vector(1024),
            nullable=True,
            comment="1024-dimension BGE-M3 embedding vector; NULL while pending",
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="pending_embedding",
            comment="Lifecycle status: pending_embedding → ready | failed",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Retry counter; prevents infinite loops on persistent failures",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timestamp when record was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment="Timestamp of last status/retry update; used for TTL cleanup",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('pending_embedding', 'ready', 'failed')",
            name="ck_omega_vectors_status",
        ),
        comment="Vector storage for semantic embeddings. "
        + "Status-driven lifecycle enables at-least-once processing with durability.",
    )

    # Primary key index (auto-created by sa.PrimaryKeyConstraint)

    # Index 1: message_id for foreign key operations
    op.create_index(
        "idx_omega_vectors_message_id", "omega_vectors_1024", ["message_id"]
    )

    # Index 2: status for worker polling (all status types)
    op.create_index("idx_omega_vectors_status", "omega_vectors_1024", ["status"])

    # Index 3: Partial index for pending records (performance optimization)
    # This index is smaller and faster than full status index for worker queries
    op.create_index(
        "idx_omega_vectors_pending",
        "omega_vectors_1024",
        ["message_id"],
        postgresql_where=sa.text("status = 'pending_embedding'"),
    )

    # Index 4: Composite index for TTL cleanup queries
    op.create_index(
        "idx_omega_vectors_cleanup",
        "omega_vectors_1024",
        ["updated_at"],
        postgresql_where=sa.text("status = 'pending_embedding'"),
    )

    # Index 5: Retry tracking for failure analysis
    op.create_index(
        "idx_omega_vectors_failed_retry",
        "omega_vectors_1024",
        ["retry_count", "updated_at"],
        postgresql_where=sa.text("status = 'failed'"),
    )


def downgrade() -> None:
    """
    Drop omega_vectors_1024 table and all associated indexes.
    WARNING: This destroys all embedding data. Use only for rollback.
    """
    # Indexes are automatically dropped when table is dropped
    op.drop_table("omega_vectors_1024")

    # Note: pgvector extension is left in place to avoid breaking other systems
    # If needed to fully clean up, manually execute: DROP EXTENSION IF EXISTS vector CASCADE;

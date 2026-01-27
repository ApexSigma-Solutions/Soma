"""Add validation queue, entities, and data lifecycle tables

Revision ID: 004_add_validation_and_entities
Revises: 9ee9fe3ca708
Create Date: 2026-01-09

Purpose: Add user-requested features for validation, entity tracking, and data lifecycle.

User Requirements:
1. Validation worker for prompt injection, malware scanning, domain relevance
2. Entity types including locations and organizations
3. Terminal sessions and workflow telemetry
4. Data lifecycle (archive → cold store → delete after 24-36 months)

Schema Design:
- All tables in 'public' schema (consistent with existing codebase)
- Entity type CHECK constraint for type safety
- Quarantine system for security validation
- Retention policy for automated lifecycle management

Deployment Notes:
- No schema breaking changes
- Backward compatible with existing migrations
- Uses existing PostgreSQL features (JSONB, CHECK constraints, indexes)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "004_add_validation_and_entities"
down_revision = "9ee9fe3ca708"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create tables for validation, entities, terminal sessions, and lifecycle management.
    """

    # =============================================================================
    # VALIDATION QUEUE (workers.validation_queue)
    # =============================================================================
    # Purpose: Security validation for incoming data
    # Features: Prompt injection detection, malware scanning, domain relevance
    op.create_table(
        "validation_queue",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column(
            "source_id",
            sa.String(255),
            nullable=False,
            comment="Reference to source record (conversation_id, event_id, etc.)",
        ),
        sa.Column(
            "source_type",
            sa.String(50),
            nullable=False,
            comment="Source table name (raw_conversations, raw_webhook_events, etc.)",
        ),
        sa.Column(
            "prompt_injection_score",
            sa.Float(),
            nullable=True,
            comment="AI-detected prompt injection probability (0-1)",
        ),
        sa.Column(
            "malware_scan_result",
            sa.String(100),
            nullable=True,
            comment="Antivirus scan result (clean/suspicious/malicious)",
        ),
        sa.Column(
            "domain_relevance_score",
            sa.Float(),
            nullable=True,
            comment="Relevance to project domain (0-1)",
        ),
        sa.Column(
            "is_quarantined",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether record is quarantined pending review",
        ),
        sa.Column(
            "validation_status",
            sa.String(32),
            nullable=False,
            server_default="pending",
            comment="Validation status: pending → approved | rejected | quarantined",
        ),
        sa.Column(
            "validated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When validation was completed",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="When validation request was created",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "validation_status IN ('pending', 'approved', 'rejected', 'quarantined')",
            name="ck_validation_queue_status",
        ),
        sa.CheckConstraint(
            "prompt_injection_score >= 0 AND prompt_injection_score <= 1",
            name="ck_validation_prompt_injection_range",
        ),
        sa.CheckConstraint(
            "domain_relevance_score >= 0 AND domain_relevance_score <= 1",
            name="ck_validation_domain_relevance_range",
        ),
        comment="Security validation queue for incoming data",
    )

    # Indexes for validation queue
    op.create_index(
        "idx_validation_queue_source",
        "validation_queue",
        ["source_type", "source_id"],
    )
    op.create_index(
        "idx_validation_queue_status",
        "validation_queue",
        ["validation_status"],
    )
    op.create_index(
        "idx_validation_queue_quarantined",
        "validation_queue",
        ["is_quarantined", "created_at"],
        postgresql_where=sa.text("is_quarantined = true"),
    )

    # =============================================================================
    # ENTITIES TABLE (knowledge.entities)
    # =============================================================================
    # Purpose: Extracted entities from conversations and documents
    # User Requested: Add locations and organizations as entity types
    op.create_table(
        "entities",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Entity name (e.g., 'OpenAI', 'London', 'John Doe')",
        ),
        sa.Column(
            "entity_type",
            sa.String(50),
            nullable=False,
            comment="Type of entity (concept, person, organization, location, etc.)",
        ),
        sa.Column(
            "canonical_form",
            sa.String(255),
            nullable=True,
            comment="Standardized name for deduplication",
        ),
        sa.Column(
            "entity_attributes",  # Renamed from 'metadata' (SQLAlchemy reserved)
            JSONB(),
            nullable=True,
            comment="Additional entity attributes (addresses, dates, etc.)",
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="When entity was first extracted",
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment="When entity was last referenced",
        ),
        sa.Column(
            "mention_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Number of times this entity has been mentioned",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "entity_type IN ('concept', 'person', 'organization', 'location', 'project', "
            "'task', 'decision', 'code_snippet', 'paper', 'website')",
            name="ck_entities_type",
        ),
        sa.UniqueConstraint(
            "name",
            "entity_type",
            name="uq_entities_name_type",
            comment="One entity per name+type combination",
        ),
        comment="Extracted entities from conversations and documents",
    )

    # Indexes for entities
    op.create_index(
        "idx_entities_type",
        "entities",
        ["entity_type"],
    )
    op.create_index(
        "idx_entities_name",
        "entities",
        ["name"],
    )
    op.create_index(
        "idx_entities_canonical",
        "entities",
        ["canonical_form"],
        postgresql_where=sa.text("canonical_form IS NOT NULL"),
    )
    op.create_index(
        "idx_entities_popularity",
        "entities",
        ["mention_count", "last_seen_at"],
    )

    # Entity-to-source mapping table (many-to-many)
    op.create_table(
        "entity_mentions",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column(
            "entity_id",
            sa.BigInteger(),
            nullable=False,
            comment="Foreign key to entities.id",
        ),
        sa.Column(
            "source_id",
            sa.String(255),
            nullable=False,
            comment="Reference to source record",
        ),
        sa.Column(
            "source_type",
            sa.String(50),
            nullable=False,
            comment="Source table name",
        ),
        sa.Column(
            "context",
            sa.Text(),
            nullable=True,
            comment="Surrounding text where entity was mentioned",
        ),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=True,
            comment="Extraction confidence (0-1)",
        ),
        sa.Column(
            "mentioned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="When this mention occurred",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            ondelete="CASCADE",
            name="fk_entity_mentions_entity_id",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_entity_mentions_confidence",
        ),
        comment="Entity occurrence tracking across sources",
    )

    op.create_index(
        "idx_entity_mentions_source",
        "entity_mentions",
        ["source_type", "source_id"],
    )

    # =============================================================================
    # TERMINAL SESSIONS (knowledge.terminal_sessions)
    # =============================================================================
    # Purpose: Aggregate terminal events into sessions for workflow analysis
    # User Requested: Terminal logs and telemetry tracking
    op.create_table(
        "terminal_sessions",
        sa.Column("session_id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user",
            sa.String(100),
            nullable=False,
            comment="System user who ran the session",
        ),
        sa.Column(
            "host",
            sa.String(255),
            nullable=False,
            comment="Hostname where session occurred",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Session start time",
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Session end time (null if active)",
        ),
        sa.Column(
            "workflow_type",
            sa.String(100),
            nullable=True,
            comment="Inferred workflow (development, testing, deployment, debugging)",
        ),
        sa.Column(
            "command_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of commands in session",
        ),
        sa.Column(
            "success_rate",
            sa.Float(),
            nullable=True,
            comment="Percentage of successful commands (0-1)",
        ),
        sa.Column(
            "productivity_score",
            sa.Float(),
            nullable=True,
            comment="Computed productivity metric",
        ),
        sa.Column(
            "efficiency_indicators",
            JSONB(),
            nullable=True,
            comment="Derived metrics (commands/min, error patterns, etc.)",
        ),
        sa.CheckConstraint(
            "success_rate IS NULL OR (success_rate >= 0 AND success_rate <= 1)",
            name="ck_terminal_sessions_success_rate",
        ),
        comment="Terminal command sessions for workflow analytics",
    )

    op.create_index(
        "idx_terminal_sessions_user",
        "terminal_sessions",
        ["user", "started_at"],
    )
    op.create_index(
        "idx_terminal_sessions_workflow",
        "terminal_sessions",
        ["workflow_type", "started_at"],
    )

    # =============================================================================
    # WORKFLOW ANALYTICS (telemetry.workflow_analytics)
    # =============================================================================
    # Purpose: Pattern mining and automation detection
    # User Requested: Workflow optimization and telemetry
    op.create_table(
        "workflow_analytics",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column(
            "workflow_name",
            sa.String(200),
            nullable=False,
            comment="Discovered workflow pattern",
        ),
        sa.Column(
            "pattern_hash",
            sa.String(64),
            nullable=False,
            comment="Hash of command sequence for deduplication",
        ),
        sa.Column(
            "command_sequence",
            JSONB(),
            nullable=False,
            comment="Ordered list of commands in workflow",
        ),
        sa.Column(
            "occurrence_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="How often this workflow has been seen",
        ),
        sa.Column(
            "total_time_saved_seconds",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Estimated time if automated",
        ),
        sa.Column(
            "is_automatable",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether workflow can be automated",
        ),
        sa.Column(
            "automation_script",
            sa.Text(),
            nullable=True,
            comment="Generated automation script (if automatable)",
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment="Most recent occurrence",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pattern_hash",
            name="uq_workflow_analytics_pattern",
        ),
        comment="Discovered workflow patterns for automation",
    )

    op.create_index(
        "idx_workflow_analytics_automatable",
        "workflow_analytics",
        ["is_automatable", "occurrence_count"],
        postgresql_where=sa.text("is_automatable = true"),
    )

    # =============================================================================
    # DATA LIFECYCLE (lifecycle.retention_policy & archived_data)
    # =============================================================================
    # Purpose: Automated data archival and deletion
    # User Requested: Archive → cold store → delete after 24-36 months
    op.create_table(
        "retention_policy",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column(
            "table_name",
            sa.String(100),
            nullable=False,
            unique=True,
            comment="Table this policy applies to",
        ),
        sa.Column(
            "active_period_months",
            sa.Integer(),
            nullable=False,
            server_default="6",
            comment="Months to keep in active database",
        ),
        sa.Column(
            "archive_period_months",
            sa.Integer(),
            nullable=False,
            server_default="24",
            comment="Total months before cold store",
        ),
        sa.Column(
            "cold_store_period_months",
            sa.Integer(),
            nullable=False,
            server_default="36",
            comment="Total months before deletion",
        ),
        sa.Column(
            "last_archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last time archival was run",
        ),
        sa.Column(
            "last_deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last time deletion was run",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Data retention policies for lifecycle management",
    )

    # Default retention policies
    op.execute(
        """
        INSERT INTO retention_policy (table_name, active_period_months, archive_period_months, cold_store_period_months)
        VALUES
            ('raw_conversations', 6, 24, 36),
            ('raw_webhook_events', 3, 12, 24),
            ('terminal_events', 12, 36, 48),
            ('omega_vectors_1024', 12, 36, 48)
        ON CONFLICT (table_name) DO NOTHING
        """
    )

    # Archived data catalog (metadata only - actual data moved to cold storage)
    op.create_table(
        "archived_data",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column(
            "source_table",
            sa.String(100),
            nullable=False,
            comment="Original table name",
        ),
        sa.Column(
            "record_count",
            sa.Integer(),
            nullable=False,
            comment="Number of records archived",
        ),
        sa.Column(
            "archive_date",
            sa.Date(),
            nullable=False,
            comment="Date of archival",
        ),
        sa.Column(
            "cold_storage_path",
            sa.String(500),
            nullable=True,
            comment="Path to archived data (S3, glacier, etc.)",
        ),
        sa.Column(
            "retention_until",
            sa.Date(),
            nullable=False,
            comment="Date when data can be deleted",
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether cold storage has been deleted",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Catalog of archived data pending deletion",
    )

    op.create_index(
        "idx_archived_data_retention",
        "archived_data",
        ["retention_until", "is_deleted"],
    )


def downgrade() -> None:
    """
    Remove all tables created in this migration.
    """
    # Drop in reverse order of creation
    op.drop_table("archived_data")
    op.drop_table("retention_policy")
    op.drop_table("workflow_analytics")
    op.drop_table("terminal_sessions")
    op.drop_table("entity_mentions")
    op.drop_table("entities")
    op.drop_table("validation_queue")

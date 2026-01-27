"""
Validation and Security Models

This module contains SQLAlchemy models for security validation,
entity extraction, terminal sessions, and data lifecycle management.
"""

from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    DateTime,
    Text,
    Boolean,
    Float,
    Index,
    UniqueConstraint,
    ForeignKeyConstraint,
    func,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship

from omega_kg.database.base import Base


# =============================================================================
# SQLAlchemy Models
# =============================================================================


class ValidationQueue(Base):
    """
    Security validation queue for incoming data.

    Features:
    - Prompt injection detection
    - Malware scanning
    - Domain relevance scoring
    - Quarantine system
    """

    __tablename__ = "validation_queue"
    __table_args__ = (
        CheckConstraint(
            "validation_status IN ('pending', 'approved', 'rejected', 'quarantined')",
            name="ck_validation_queue_status",
        ),
        CheckConstraint(
            "prompt_injection_score >= 0 AND prompt_injection_score <= 1",
            name="ck_validation_prompt_injection_range",
        ),
        CheckConstraint(
            "domain_relevance_score >= 0 AND domain_relevance_score <= 1",
            name="ck_validation_domain_relevance_range",
        ),
        Index("idx_validation_queue_source", "source_type", "source_id"),
        Index("idx_validation_queue_status", "validation_status"),
        Index(
            "idx_validation_queue_quarantined",
            "is_quarantined",
            "created_at",
            postgresql_where="is_quarantined = true",
        ),
        {"comment": "Security validation queue for incoming data"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_id = Column(
        String(255),
        nullable=False,
        comment="Reference to source record (conversation_id, event_id, etc.)",
    )
    source_type = Column(
        String(50),
        nullable=False,
        comment="Source table name (raw_conversations, raw_webhook_events, etc.)",
    )
    prompt_injection_score = Column(
        Float,
        nullable=True,
        comment="AI-detected prompt injection probability (0-1)",
    )
    malware_scan_result = Column(
        String(100),
        nullable=True,
        comment="Antivirus scan result (clean/suspicious/malicious)",
    )
    domain_relevance_score = Column(
        Float,
        nullable=True,
        comment="Relevance to project domain (0-1)",
    )
    is_quarantined = Column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether record is quarantined pending review",
    )
    validation_status = Column(
        String(32),
        nullable=False,
        server_default="pending",
        comment="Validation status: pending -> approved | rejected | quarantined",
    )
    validated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When validation was completed",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When validation request was created",
    )

    def __repr__(self):
        return f"<ValidationQueue(id={self.id}, status='{self.validation_status}', source='{self.source_type}:{self.source_id}')>"


class Entity(Base):
    """
    Extracted entities from conversations and documents.

    Entity Types (User Requested: locations and organizations added):
    - concept, person, organization, location, project, task, decision,
      code_snippet, paper, website
    """

    __tablename__ = "entities"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('concept', 'person', 'organization', 'location', 'project', "
            "'task', 'decision', 'code_snippet', 'paper', 'website')",
            name="ck_entities_type",
        ),
        UniqueConstraint(
            "name",
            "entity_type",
            name="uq_entities_name_type",
            comment="One entity per name+type combination",
        ),
        Index("idx_entities_type", "entity_type"),
        Index("idx_entities_name", "name"),
        Index(
            "idx_entities_canonical",
            "canonical_form",
            postgresql_where="canonical_form IS NOT NULL",
        ),
        Index("idx_entities_popularity", "mention_count", "last_seen_at"),
        {"comment": "Extracted entities from conversations and documents"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(
        String(255),
        nullable=False,
        comment="Entity name (e.g., 'OpenAI', 'London', 'John Doe')",
    )
    entity_type = Column(
        String(50),
        nullable=False,
        comment="Type of entity (concept, person, organization, location, etc.)",
    )
    canonical_form = Column(
        String(255),
        nullable=True,
        comment="Standardized name for deduplication",
    )
    entity_attributes = Column(
        "entity_attributes",  # Renamed from 'metadata' (SQLAlchemy reserved)
        JSONB,
        nullable=True,
        comment="Additional entity attributes (addresses, dates, etc.)",
    )
    first_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When entity was first extracted",
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When entity was last referenced",
    )
    mention_count = Column(
        Integer,
        nullable=False,
        server_default="1",
        comment="Number of times this entity has been mentioned",
    )

    # Relationship to mentions
    mentions = relationship(
        "EntityMention",
        back_populates="entity",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Entity(id={self.id}, name='{self.name}', type='{self.entity_type}')>"


class EntityMention(Base):
    """
    Entity occurrence tracking across sources.

    Links entities to the documents/conversations where they appear.
    """

    __tablename__ = "entity_mentions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            ondelete="CASCADE",
            name="fk_entity_mentions_entity_id",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_entity_mentions_confidence",
        ),
        Index("idx_entity_mentions_source", "source_type", "source_id"),
        {"comment": "Entity occurrence tracking across sources"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    entity_id = Column(
        BigInteger,
        nullable=False,
        comment="Foreign key to entities.id",
    )
    source_id = Column(
        String(255),
        nullable=False,
        comment="Reference to source record",
    )
    source_type = Column(
        String(50),
        nullable=False,
        comment="Source table name",
    )
    context = Column(
        Text,
        nullable=True,
        comment="Surrounding text where entity was mentioned",
    )
    confidence_score = Column(
        Float,
        nullable=True,
        comment="Extraction confidence (0-1)",
    )
    mentioned_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this mention occurred",
    )

    # Relationship to entity
    entity = relationship("Entity", back_populates="mentions")

    def __repr__(self):
        return f"<EntityMention(id={self.id}, entity_id={self.entity_id}, source='{self.source_type}:{self.source_id}')>"


class TerminalSession(Base):
    """
    Terminal command sessions for workflow analytics.

    Aggregates terminal_events into sessions for pattern mining
    and productivity analysis.
    """

    __tablename__ = "terminal_sessions"
    __table_args__ = (
        CheckConstraint(
            "success_rate IS NULL OR (success_rate >= 0 AND success_rate <= 1)",
            name="ck_terminal_sessions_success_rate",
        ),
        Index("idx_terminal_sessions_user", "user", "started_at"),
        Index("idx_terminal_sessions_workflow", "workflow_type", "started_at"),
        {"comment": "Terminal command sessions for workflow analytics"},
    )

    session_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user = Column(
        String(100),
        nullable=False,
        comment="System user who ran the session",
    )
    host = Column(
        String(255),
        nullable=False,
        comment="Hostname where session occurred",
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Session start time",
    )
    ended_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Session end time (null if active)",
    )
    workflow_type = Column(
        String(100),
        nullable=True,
        comment="Inferred workflow (development, testing, deployment, debugging)",
    )
    command_count = Column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of commands in session",
    )
    success_rate = Column(
        Float,
        nullable=True,
        comment="Percentage of successful commands (0-1)",
    )
    productivity_score = Column(
        Float,
        nullable=True,
        comment="Computed productivity metric",
    )
    efficiency_indicators = Column(
        JSONB,
        nullable=True,
        comment="Derived metrics (commands/min, error patterns, etc.)",
    )

    def __repr__(self):
        return f"<TerminalSession(session_id={self.session_id}, user='{self.user}', workflow='{self.workflow_type}')>"


class WorkflowAnalytics(Base):
    """
    Discovered workflow patterns for automation.

    Identifies repeated command sequences that can be automated
    to save time and reduce errors.
    """

    __tablename__ = "workflow_analytics"
    __table_args__ = (
        UniqueConstraint(
            "pattern_hash",
            name="uq_workflow_analytics_pattern",
        ),
        Index(
            "idx_workflow_analytics_automatable",
            "is_automatable",
            "occurrence_count",
            postgresql_where="is_automatable = true",
        ),
        {"comment": "Discovered workflow patterns for automation"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workflow_name = Column(
        String(200),
        nullable=False,
        comment="Discovered workflow pattern",
    )
    pattern_hash = Column(
        String(64),
        nullable=False,
        comment="Hash of command sequence for deduplication",
    )
    command_sequence = Column(
        JSONB,
        nullable=False,
        comment="Ordered list of commands in workflow",
    )
    occurrence_count = Column(
        Integer,
        nullable=False,
        server_default="1",
        comment="How often this workflow has been seen",
    )
    total_time_saved_seconds = Column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Estimated time if automated",
    )
    is_automatable = Column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether workflow can be automated",
    )
    automation_script = Column(
        Text,
        nullable=True,
        comment="Generated automation script (if automatable)",
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Most recent occurrence",
    )

    def __repr__(self):
        return f"<WorkflowAnalytics(id={self.id}, name='{self.workflow_name}', automatable={self.is_automatable})>"


class RetentionPolicy(Base):
    """
    Data retention policies for lifecycle management.

    Defines how long data should be kept before archival/deletion.
    """

    __tablename__ = "retention_policy"
    __table_args__ = (
        UniqueConstraint("table_name", name="uq_retention_policy_table"),
        {"comment": "Data retention policies for lifecycle management"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Table this policy applies to",
    )
    active_period_months = Column(
        Integer,
        nullable=False,
        server_default="6",
        comment="Months to keep in active database",
    )
    archive_period_months = Column(
        Integer,
        nullable=False,
        server_default="24",
        comment="Total months before cold store",
    )
    cold_store_period_months = Column(
        Integer,
        nullable=False,
        server_default="36",
        comment="Total months before deletion",
    )
    last_archived_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time archival was run",
    )
    last_deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time deletion was run",
    )

    def __repr__(self):
        return f"<RetentionPolicy(table='{self.table_name}', active={self.active_period_months}m, archive={self.archive_period_months}m)>"


class ArchivedData(Base):
    """
    Catalog of archived data pending deletion.

    Tracks data that has been moved to cold storage and when it can be deleted.
    """

    __tablename__ = "archived_data"
    __table_args__ = (
        Index(
            "idx_archived_data_retention",
            "retention_until",
            "is_deleted",
        ),
        {"comment": "Catalog of archived data pending deletion"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_table = Column(
        String(100),
        nullable=False,
        comment="Original table name",
    )
    record_count = Column(
        Integer,
        nullable=False,
        comment="Number of records archived",
    )
    archive_date = Column(
        DateTime,
        nullable=False,
        comment="Date of archival",
    )
    cold_storage_path = Column(
        String(500),
        nullable=True,
        comment="Path to archived data (S3, glacier, etc.)",
    )
    retention_until = Column(
        DateTime,
        nullable=False,
        comment="Date when data can be deleted",
    )
    is_deleted = Column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether cold storage has been deleted",
    )

    def __repr__(self):
        return f"<ArchivedData(id={self.id}, table='{self.source_table}', retention_until={self.retention_until})>"


# =============================================================================
# Pydantic Models for API
# =============================================================================


class EntityType(str):
    """Valid entity types including user-requested locations and organizations."""

    CONCEPT = "concept"
    PERSON = "person"
    ORGANIZATION = "organization"  # User requested
    LOCATION = "location"  # User requested
    PROJECT = "project"
    TASK = "task"
    DECISION = "decision"
    CODE_SNIPPET = "code_snippet"
    PAPER = "paper"
    WEBSITE = "website"


class ValidationStatus(str):
    """Validation workflow statuses."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class WorkflowType(str):
    """Common terminal workflow patterns."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"


# Export all models
__all__ = [
    "ValidationQueue",
    "Entity",
    "EntityMention",
    "TerminalSession",
    "WorkflowAnalytics",
    "RetentionPolicy",
    "ArchivedData",
    "EntityType",
    "ValidationStatus",
    "WorkflowType",
]

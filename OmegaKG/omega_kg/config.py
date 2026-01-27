"""
Omega_KG Configuration Module

Central configuration for PostgreSQL vector storage, embedding services, and async workers.
Supports environment-specific overrides (dev/stable) via .env file.

Environment-Specific Variables (via .env):
- OMEGA_ENV: 'dev' or 'stable' (defaults to 'dev')
- POSTGRES_*: Database connection parameters (inherited from settings.py)

Shared Constants:
- VECTOR_EMBEDDING_DIMENSION: 1024 (BGE-M3 native output)
- VECTOR_EMBEDDING_MAX_RETRIES: 3 (failed embedding retry attempts)
- VECTOR_TABLE_NAME: 'omega_vectors_1024' (shared across dev/stable)
- VECTOR_STATUS_*: Status values for embedding lifecycle

Phase Integration:
- Phase 7 (TN-LINEAR-07): Vector enrichment now backed by PostgreSQL instead of Neo4j
- Async worker pattern: Ensures at-least-once processing with database durability
"""

import os
from enum import Enum

from omega_kg.settings import settings

# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================
OMEGA_ENV = os.getenv("OMEGA_ENV", "dev")
"""Target environment: 'dev' or 'stable'. Controls database selection and logging."""

IS_DEV = OMEGA_ENV == "dev"
IS_STABLE = OMEGA_ENV == "stable"


# ============================================================================
# POSTGRESQL CONNECTION (inherited from settings.py via Bitwarden/fallback)
# ============================================================================
# These mirror settings.py but are re-exported here for clarity in vector module imports
POSTGRES_USER = settings.postgres_user
"""PostgreSQL user (from settings.postgres_user)"""

POSTGRES_PASSWORD = settings.postgres_password
"""PostgreSQL password (from settings.postgres_password, Bitwarden-injected if available)"""

POSTGRES_SERVER = settings.postgres_server
"""PostgreSQL host (from settings.postgres_server)"""

POSTGRES_PORT = settings.postgres_port
"""PostgreSQL port (from settings.postgres_port)"""

POSTGRES_DB = settings.postgres_db
"""PostgreSQL database name (from settings.postgres_db, env-specific: omega_kg_dev or omega_kg_stable)"""

DATABASE_URL = settings.database_url
"""Full async PostgreSQL connection string (postgresql+asyncpg://...), used by SQLAlchemy"""


# ============================================================================
# VECTOR STORAGE CONSTANTS
# ============================================================================
VECTOR_TABLE_NAME = "omega_vectors_1024"
"""Table name for vector embeddings. Consistent across dev/stable to simplify migrations."""

VECTOR_EMBEDDING_DIMENSION = 1024
"""BGE-M3 embedding output dimension. Critical: must match model and database column."""

VECTOR_EMBEDDING_MODEL = "bge-m3:567m"
"""Ollama model name for embeddings. Pulled independently per environment."""

VECTOR_EMBEDDING_PROVIDER = settings.embedding_provider
"""Primary embedding provider (default: 'ollama'). Fallback to nano-gpt, gemini, or mock."""


# ============================================================================
# ASYNC WORKER CONFIGURATION
# ============================================================================
VECTOR_EMBEDDING_MAX_RETRIES = int(os.getenv("VECTOR_EMBEDDING_MAX_RETRIES", "3"))
"""Maximum retry attempts for failed embedding jobs before manual intervention."""

VECTOR_WORKER_POLL_INTERVAL_SECONDS = int(
    os.getenv("VECTOR_WORKER_POLL_INTERVAL_SECONDS", "10")
)
"""Interval (seconds) between polling for pending embeddings. Lower = more responsive, higher = less DB load."""

VECTOR_WORKER_BATCH_SIZE = int(os.getenv("VECTOR_WORKER_BATCH_SIZE", "10"))
"""Number of pending embeddings to process per poll cycle."""

VECTOR_WORKER_TIMEOUT_SECONDS = int(os.getenv("VECTOR_WORKER_TIMEOUT_SECONDS", "120"))
"""Timeout (seconds) for embedding generation. Prevents hanging on Ollama disconnection."""

VECTOR_CLEANUP_TTL_DAYS = int(os.getenv("VECTOR_CLEANUP_TTL_DAYS", "7"))
"""Time-to-live (days) for stale pending_embedding records before cleanup."""

VECTOR_CLEANUP_ENABLED = os.getenv("VECTOR_CLEANUP_ENABLED", "true").lower() == "true"
"""Enable automatic cleanup of expired pending embeddings."""


# ============================================================================
# VECTOR STATUS ENUM
# ============================================================================
class VectorStatus(str, Enum):
    """Status lifecycle for embedding records in omega_vectors_1024."""

    PENDING_EMBEDDING = "pending_embedding"
    """Record created; awaiting embedding generation by worker."""

    READY = "ready"
    """Embedding successfully generated and stored; ready for semantic search."""

    FAILED = "failed"
    """Embedding generation failed after max retries; requires manual intervention or retry."""

    def __str__(self) -> str:
        return self.value


# ============================================================================
# NEO4J NODE TYPE TRACKING (for polymorphic vector storage)
# ============================================================================
SUPPORTED_NODE_TYPES = ("ChatMessage", "LinearIssue", "Decision", "Task")
"""Supported Neo4j node types for vector storage. Used to populate node_label column."""

DEFAULT_NODE_TYPE = "ChatMessage"
"""Default node type when source is ambiguous or unspecified."""


# ============================================================================
# LINEAR STATUS MAPPING
# ============================================================================
LINEAR_STATUS_MAP = {
    "Backlog": "draft",
    "Todo": "ready",
    "In Progress": "active",
    "Done": "completed",
    "Canceled": "archived",
}
"""Maps Linear issue states to Obsidian task statuses."""


# ============================================================================
# OLLAMA CONFIGURATION (inherited from settings.py)
# ============================================================================
OLLAMA_BASE_URL = settings.ollama_base_url
"""Ollama service base URL (default: http://localhost:11434)"""

OLLAMA_EMBEDDING_ENDPOINT = f"{OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
"""Full endpoint URL for Ollama embedding requests."""


# ============================================================================
# LOGGING & MONITORING
# ============================================================================
ENABLE_VECTOR_DEBUG_LOGGING = (
    os.getenv("ENABLE_VECTOR_DEBUG_LOGGING", "false").lower() == "true"
)
"""Enable verbose debug logging for vector operations."""

VECTOR_METRICS_ENABLED = os.getenv("VECTOR_METRICS_ENABLED", "true").lower() == "true"
"""Enable collection of vector worker metrics (counts, latencies)."""


# ============================================================================
# MIGRATION & SCHEMA
# ============================================================================
ALEMBIC_MIGRATIONS_PATH = "alembic/versions"
"""Path to Alembic revision files (relative to project root)."""

VECTOR_SCHEMA_VERSION = "1.0.0"
"""Version of the omega_vectors_1024 schema. Increment on breaking changes."""


# ============================================================================
# ENVIRONMENT-SPECIFIC DEBUGGING
# ============================================================================
def log_config_summary() -> str:
    """
    Generate a summary of active configuration for logging at startup.

    Returns:
        str: Multi-line configuration summary
    """
    return f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                    Omega_KG Vector Configuration                          ║
╚════════════════════════════════════════════════════════════════════════════╝
Environment:                 {OMEGA_ENV}
PostgreSQL Host:             {POSTGRES_SERVER}:{POSTGRES_PORT}
PostgreSQL Database:         {POSTGRES_DB}
Vector Table:                {VECTOR_TABLE_NAME}
Embedding Dimension:         {VECTOR_EMBEDDING_DIMENSION}
Embedding Provider:          {VECTOR_EMBEDDING_PROVIDER}
Ollama Base URL:             {OLLAMA_BASE_URL}
Worker Poll Interval:        {VECTOR_WORKER_POLL_INTERVAL_SECONDS}s
Worker Batch Size:           {VECTOR_WORKER_BATCH_SIZE}
Max Retries:                 {VECTOR_EMBEDDING_MAX_RETRIES}
Cleanup TTL:                 {VECTOR_CLEANUP_TTL_DAYS} days
Cleanup Enabled:             {VECTOR_CLEANUP_ENABLED}
Debug Logging:               {ENABLE_VECTOR_DEBUG_LOGGING}
Metrics Enabled:             {VECTOR_METRICS_ENABLED}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# Expose for import
__all__ = [
    # Environment
    "OMEGA_ENV",
    "IS_DEV",
    "IS_STABLE",
    # PostgreSQL
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_SERVER",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "DATABASE_URL",
    # Vector Storage
    "VECTOR_TABLE_NAME",
    "VECTOR_EMBEDDING_DIMENSION",
    "VECTOR_EMBEDDING_MODEL",
    "VECTOR_EMBEDDING_PROVIDER",
    # Worker Configuration
    "VECTOR_EMBEDDING_MAX_RETRIES",
    "VECTOR_WORKER_POLL_INTERVAL_SECONDS",
    "VECTOR_WORKER_BATCH_SIZE",
    "VECTOR_WORKER_TIMEOUT_SECONDS",
    "VECTOR_CLEANUP_TTL_DAYS",
    "VECTOR_CLEANUP_ENABLED",
    # Status Enum
    "VectorStatus",
    # Neo4j Node Types
    "SUPPORTED_NODE_TYPES",
    "DEFAULT_NODE_TYPE",
    # Linear Integration
    "LINEAR_STATUS_MAP",
    # Ollama
    "OLLAMA_BASE_URL",
    "OLLAMA_EMBEDDING_ENDPOINT",
    # Monitoring
    "ENABLE_VECTOR_DEBUG_LOGGING",
    "VECTOR_METRICS_ENABLED",
    # Schema
    "ALEMBIC_MIGRATIONS_PATH",
    "VECTOR_SCHEMA_VERSION",
    # Utilities
    "log_config_summary",
]

"""
Dead Letter Queue Handler

Persists failed webhook payloads to PostgreSQL for later processing.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import asyncpg

logger = logging.getLogger(__name__)


async def write_to_dlq(
    payload: Dict[str, Any],
    error_message: str,
    correlation_id: str,
    postgres_dsn: str,
) -> Optional[str]:
    """
    Persist failed payload to dead letter queue.

    Establishes database connection, serializes payload to JSON,
    inserts record with error context, and properly closes connection.

    Args:
        payload: Failed webhook payload dictionary
        error_message: Error description for failure context
        correlation_id: Request ID for traceability
        postgres_dsn: PostgreSQL connection string

    Returns:
        Optional[str]: DLQ record ID if successful, None otherwise

    Raises:
        Exception: Logs database connectivity issues but does not raise
    """
    dlq_id = str(uuid.uuid4())
    created_at = datetime.utcnow()

    try:
        conn = await asyncpg.connect(postgres_dsn)
        try:
            payload_json = json.dumps(payload, default=str)

            await conn.execute(
                """
                INSERT INTO ingest_failures (
                    id,
                    payload,
                    error_message,
                    correlation_id,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5)
                """,
                dlq_id,
                payload_json,
                error_message,
                correlation_id,
                created_at,
            )

            logger.info(
                "DLQ write successful",
                extra={
                    "dlq_id": dlq_id,
                    "correlation_id": correlation_id,
                    "error_message": error_message,
                    "timestamp": created_at.isoformat(),
                },
            )

            return dlq_id

        finally:
            await conn.close()

    except (asyncpg.PostgresConnectionError, asyncpg.PostgresError) as e:
        logger.error(
            "Database connection error writing to DLQ",
            extra={
                "dlq_id": dlq_id,
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": created_at.isoformat(),
            },
            exc_info=True,
        )
        return None

    except Exception as e:
        logger.error(
            "Unexpected error writing to DLQ",
            extra={
                "dlq_id": dlq_id,
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": created_at.isoformat(),
            },
            exc_info=True,
        )
        return None


async def create_dlq_table(postgres_dsn: str) -> bool:
    """
    Create dead letter queue table if it doesn't exist.

    Args:
        postgres_dsn: PostgreSQL connection string

    Returns:
        bool: True if table created or exists, False on error
    """
    try:
        conn = await asyncpg.connect(postgres_dsn)
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingest_failures (
                    id UUID PRIMARY KEY,
                    payload JSONB NOT NULL,
                    error_message TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
                """
            )

            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ingest_failures_created_at
                ON ingest_failures (created_at DESC)
                """
            )

            logger.info("DLQ table verified/created successfully")
            return True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(
            "Failed to create DLQ table",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        return False

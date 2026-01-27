"""
Quipu Database Module
Handles PostgreSQL operations for heartbeat monitoring using synchronous psycopg2.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import asyncpg
import psycopg2

from omega_kg.settings import settings

logger = logging.getLogger("QuipuDB")

# SQL Definitions
INIT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS system_heartbeats (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,
    latency_ms INTEGER,
    model_loaded VARCHAR(100),
    meta JSONB
);
CREATE INDEX IF NOT EXISTS idx_heartbeat_timestamp ON system_heartbeats(timestamp DESC);
"""

INSERT_HEARTBEAT_SQL = """
INSERT INTO system_heartbeats (service_name, timestamp, status, latency_ms, model_loaded, meta)
VALUES ($1, $2, $3, $4, $5, $6);
"""


async def get_db_connection() -> Optional[asyncpg.Connection]:
    """Establishes connection to PostgreSQL using settings."""
    try:
        # Remove SQLAlchemy-specific scheme suffix for asyncpg compatibility
        conn_string = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        return await asyncpg.connect(conn_string)
    except (psycopg2.OperationalError, Exception) as e:
        logger.error(f"Database connection failed: {e}")
        return None


async def init_heartbeat_table() -> bool:
    """Initialize the system_heartbeats table if it doesn't exist."""
    conn = await get_db_connection()
    if not conn:
        return False
    try:
        await conn.execute(INIT_TABLE_SQL)
        logger.info("Heartbeat table verified in database.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize heartbeat table: {e}")
        return False
    finally:
        await conn.close()


async def insert_heartbeat(
    service_name: str,
    timestamp: datetime,
    status: str,
    latency_ms: int,
    model_loaded: Optional[str],
    meta: Dict[str, Any],
) -> bool:
    """Insert a heartbeat record into the database."""
    conn = await get_db_connection()
    if not conn:
        return False
    try:
        # Convert meta dict to JSON string for JSONB column
        meta_json = json.dumps(meta) if meta else "{}"
        await conn.execute(
            INSERT_HEARTBEAT_SQL,
            service_name,
            timestamp,
            status,
            latency_ms,
            model_loaded,
            meta_json,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to insert heartbeat: {e}")
        return False
    finally:
        await conn.close()
        await conn.close()

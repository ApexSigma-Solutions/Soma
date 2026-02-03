"""Raw Lake Asset - Polls soma_sensory_lake for pending records.

Implements TN-SOMA-202: Dagster asset that polls Postgres raw_lake table
for processing_status='PENDING' records with batch size limit of 50.

This is the entry point for the digestion pipeline in InGest (The Stomach).
"""

from typing import Any, Dict, List

from dagster import AssetExecutionContext, Config, asset
from pydantic import Field

from ..resources import PostgresResource


class RawLakeConfig(Config):
    """Configuration for raw lake polling."""

    batch_size: int = Field(
        default=50,
        description="Maximum number of records to process per run (CST-IDEM-002)",
    )


@asset(
    description="Poll raw_lake for PENDING records (sensory input for digestion)",
    compute_kind="postgres",
    group_name="digestion_pipeline",
)
async def raw_conversations(
    context: AssetExecutionContext,
    config: RawLakeConfig,
    postgres: PostgresResource,
) -> List[Dict[str, Any]]:
    """Fetch pending records from soma_sensory_lake.

    This asset implements Stage 2.1 of SimpleMem v2.0:
    - Poll raw_lake for processing_status = 'PENDING'
    - Limit batch to 50 rows to prevent memory overflow
    - Return records for downstream processing

    Returns:
        List of raw records with id, source, event_type, payload, created_at
    """
    context.log.info(f"Polling raw_lake (batch_size={config.batch_size})")

    conn = await postgres.get_connection()

    try:
        # Query raw_lake for PENDING records
        rows = await conn.fetch(
            """
            SELECT 
                id,
                source,
                event_type,
                payload,
                client_ip,
                created_at
            FROM raw_lake
            WHERE processing_status = 'PENDING'
            ORDER BY created_at ASC
            LIMIT $1
            """,
            config.batch_size,
        )

        if not rows:
            context.log.info("No pending records in raw_lake")
            return []

        context.log.info(f"Found {len(rows)} pending records")

        # Convert to list of dicts
        records = [
            {
                "id": str(row["id"]),
                "source": row["source"],
                "event_type": row["event_type"],
                "payload": row["payload"],
                "client_ip": row["client_ip"],
                "created_at": row["created_at"].isoformat()
                if row["created_at"]
                else None,
            }
            for row in rows
        ]

        return records

    finally:
        await conn.close()

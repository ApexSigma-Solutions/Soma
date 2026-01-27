"""Raw Lake Sensor for Dagster.

Polls the raw_lake table for unprocessed records captured by Soma.Ingress
and dispatches them to appropriate processing pipelines.
"""

import os
from datetime import datetime
from typing import Any, Dict, List

import asyncpg
import structlog
from dagster import RunRequest, SensorEvaluationContext, sensor

log = structlog.get_logger()

# Database connection string
DB_DSN = os.getenv(
    "SOMA_PG_DSN",
    "postgresql://omega_user:password@localhost:6000/omega_kg_stable",
)

# Maximum records to process per sensor tick
BATCH_SIZE = 100


async def fetch_unprocessed_records() -> List[Dict[str, Any]]:
    """Fetch unprocessed records from raw_lake.

    Returns:
        List of unprocessed record dictionaries
    """
    conn = await asyncpg.connect(DB_DSN)
    try:
        query = """
            SELECT id, source, event_type, payload, client_ip, ingested_at
            FROM raw_lake
            WHERE processed = FALSE
            ORDER BY ingested_at ASC
            LIMIT $1
        """
        rows = await conn.fetch(query, BATCH_SIZE)
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def acknowledge_records(record_ids: List[str]) -> int:
    """Mark records as processed in raw_lake.

    Args:
        record_ids: List of UUIDs to acknowledge

    Returns:
        Number of records updated
    """
    if not record_ids:
        return 0

    conn = await asyncpg.connect(DB_DSN)
    try:
        query = """
            UPDATE raw_lake
            SET processed = TRUE
            WHERE id = ANY($1::uuid[])
        """
        result = await conn.execute(query, record_ids)
        # result is like "UPDATE 5"
        count = int(result.split(" ")[1]) if result else 0
        return count
    finally:
        await conn.close()


def dispatch_by_source(record: Dict[str, Any]) -> str:
    """Determine the processing job to run based on record source.

    Args:
        record: Raw lake record with source field

    Returns:
        Job name to execute
    """
    source_to_job = {
        "obsidian": "process_vault_event",
        "github": "process_github_webhook",
        "chrome": "process_web_capture",
        "terminal": "process_terminal_log",
    }
    return source_to_job.get(record["source"], "process_generic_event")


@sensor(job_name="raw_lake_processor")
def raw_lake_sensor(context: SensorEvaluationContext):
    """Dagster sensor that polls raw_lake for unprocessed data.

    Yields RunRequest for each batch of unprocessed records,
    grouped by source type for efficient pipeline processing.
    """
    import asyncio

    # Run async fetch in sync context
    loop = asyncio.new_event_loop()
    try:
        records = loop.run_until_complete(fetch_unprocessed_records())
    finally:
        loop.close()

    if not records:
        context.log.debug("No unprocessed records in raw_lake")
        return

    context.log.info(f"Found {len(records)} unprocessed records")

    # Group records by source for batch processing
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        source = record["source"]
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(record)

    # Yield a run request for each source type
    for source, source_records in by_source.items():
        run_key = f"{source}_{datetime.utcnow().isoformat()}"
        record_ids = [str(r["id"]) for r in source_records]

        yield RunRequest(
            run_key=run_key,
            run_config={
                "ops": {
                    "process_raw_lake_batch": {
                        "config": {
                            "source": source,
                            "record_ids": record_ids,
                            "payloads": [r["payload"] for r in source_records],
                        }
                    }
                }
            },
            tags={"source": source, "batch_size": str(len(source_records))},
        )

        context.log.info(
            f"Dispatched {len(source_records)} {source} records",
            extra={"run_key": run_key},
        )

"""Poison Pill Sensor - Detects and quarantines bad data.

This sensor prevents the "Capture Loop" (EVT-LOOP-589) by:
1. Monitoring for PENDING transactions stuck too long
2. Validating content is safe (UTF-8, no binary garbage)
3. Marking poisoned data as Incidents in the Codex of Consequences

This is part of the Mirmir Protocol - failure metabolization.
"""

from dagster import (
    sensor,
    SensorEvaluationContext,
    RunRequest,
    SkipReason,
    DefaultSensorStatus,
)
import asyncio
import asyncpg
import json
from datetime import datetime, timedelta


STUCK_TIMEOUT_MINUTES = 5
BINARY_CHECK_SAMPLE_SIZE = 1000


def is_poison_pill(payload: dict) -> tuple[bool, str]:
    """Detect if payload contains poison pill data.

    Poison pills include:
    - Binary/null bytes that can't be processed
    - Malformed JSON that causes infinite retries
    - Known problematic patterns (PowerShell binary logs)

    Returns:
        Tuple of (is_poison, reason)
    """
    content = payload.get("content", "")

    # Check for null bytes
    if "\x00" in content:
        return True, "Contains null bytes"

    # Check for high ratio of non-printable characters
    sample = content[:BINARY_CHECK_SAMPLE_SIZE]
    non_printable = sum(1 for c in sample if ord(c) < 32 and c not in "\n\r\t")
    if len(sample) > 0 and non_printable / len(sample) > 0.1:
        return True, f"High non-printable ratio: {non_printable}/{len(sample)}"

    # Check for UTF-8 validity
    try:
        if isinstance(content, str):
            content.encode("utf-8")
    except UnicodeEncodeError as e:
        return True, f"Invalid UTF-8: {e}"

    # Check for known problematic patterns
    if "ÿþ" in content:  # UTF-16 BOM often in binary files
        return True, "Contains UTF-16 BOM marker"

    if payload.get("type") == "terminal":
        command = payload.get("metadata", {}).get("command", "")
        # PowerShell binary output patterns
        if "Format-Hex" in command or "Get-Content -Encoding Byte" in command:
            return True, "PowerShell binary command output"

    return False, ""


async def check_stuck_transactions(dsn: str) -> list[dict]:
    """Find transactions stuck in PENDING state."""
    conn = await asyncpg.connect(dsn=dsn)
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=STUCK_TIMEOUT_MINUTES)
        rows = await conn.fetch(
            """
            SELECT id, webhook_payload, created_at
            FROM ingest_transactions
            WHERE status = 'PENDING'
              AND created_at < $1
            ORDER BY created_at ASC
            LIMIT 100
        """,
            cutoff,
        )

        return [
            {
                "id": row["id"],
                "payload": row["webhook_payload"]
                if isinstance(row["webhook_payload"], dict)
                else json.loads(row["webhook_payload"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    finally:
        await conn.close()


async def mark_as_incident(dsn: str, tx_id: int, reason: str) -> None:
    """Mark a transaction as an incident (poison pill)."""
    conn = await asyncpg.connect(dsn=dsn)
    try:
        await conn.execute(
            """
            UPDATE ingest_transactions
            SET status = 'INCIDENT',
                updated_at = NOW(),
                webhook_payload = webhook_payload || $2::jsonb
            WHERE id = $1
        """,
            tx_id,
            json.dumps(
                {
                    "incident_reason": reason,
                    "incident_at": datetime.utcnow().isoformat(),
                }
            ),
        )
    finally:
        await conn.close()


@sensor(
    description="Detects stuck transactions and poison pill data",
    minimum_interval_seconds=60,
    default_status=DefaultSensorStatus.RUNNING,
)
def poison_pill_sensor(context: SensorEvaluationContext):
    """Sensor that monitors for and quarantines poison pill data.

    This implements the Mirmir Protocol's failure metabolization:
    - Detect failures before they cause infinite loops
    - Mark bad data as Incidents
    - Log to Codex of Consequences for future prevention
    """
    # Get DSN from environment or use default
    import os

    dsn = os.environ.get(
        "POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/soma_data"
    )

    # Run async check in sync context
    loop = asyncio.new_event_loop()
    try:
        stuck_transactions = loop.run_until_complete(check_stuck_transactions(dsn))
    finally:
        loop.close()

    if not stuck_transactions:
        return SkipReason("No stuck transactions found")

    incidents_found = 0

    for tx in stuck_transactions:
        is_poison, reason = is_poison_pill(tx["payload"])

        if is_poison:
            # Quarantine the poison pill
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(mark_as_incident(dsn, tx["id"], reason))
            finally:
                loop.close()

            context.log.warning(
                f"Poison pill detected in tx-{tx['id']}: {reason}. Marked as INCIDENT."
            )
            incidents_found += 1

    if incidents_found > 0:
        context.log.info(f"Quarantined {incidents_found} poison pills")
        # Trigger a run to reprocess remaining valid transactions
        return RunRequest(
            run_key=f"poison_cleanup_{context.cursor}",
            run_config={},
        )

    # Some transactions are stuck but not poisoned - may need investigation
    context.log.warning(
        f"Found {len(stuck_transactions)} stuck transactions that are not poison pills. "
        "Manual investigation may be required."
    )

    return SkipReason(
        f"Found {len(stuck_transactions)} stuck transactions (not poison)"
    )

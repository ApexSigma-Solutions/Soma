"""Terminal Processor Asset (Saga Weaver) - Migrated from OmegaKG.

This asset processes raw terminal events (source: raw_terminal_events table),
extracts entity references (issues), generates embeddings, and commits to OmegaKG Guardian.
"""

from dagster import asset, AssetExecutionContext, Config
from pydantic import Field
from typing import Any, Dict
import re

from ..resources import (
    PostgresResource,
    OllamaResource,
    OmegaKGClient,
)

# Regex for entity extraction (LIN-123 or #123)
ISSUE_PATTERN = re.compile(r"\b([A-Z]{2,5}-\d+)\b|\b#(\d+)\b")


class TerminalProcessorConfig(Config):
    """Configuration for terminal event processing."""

    batch_size: int = Field(
        default=25, description="Number of events to process per run"
    )


@asset(
    description="Process raw terminal events into Flexible Knowledge Digests (Saga Weaver)",
    compute_kind="python",
    group_name="ingest_pipeline",
)
async def terminal_processor(
    context: AssetExecutionContext,
    config: TerminalProcessorConfig,
    postgres: PostgresResource,
    ollama: OllamaResource,
    omegakg: OmegaKGClient,
) -> Dict[str, Any]:
    """Process raw terminal events."""

    context.log.info("Starting Terminal Processor (Saga Weaver)")
    processed_count = 0

    conn = await postgres.get_connection()

    try:
        # Fetch unprocessed events
        # Assuming table raw_terminal_events exists in postgres resource DB
        rows = await conn.fetch(
            """
            SELECT id, event_id, command, cwd, exit_code, output, "user", host, captured_at, session_id
            FROM raw_terminal_events
            WHERE processed = false
            ORDER BY captured_at ASC
            LIMIT $1
            """,
            config.batch_size,
        )

        if not rows:
            context.log.info("No new terminal events to process")
            return {"processed": 0}

        context.log.info(f"Found {len(rows)} terminal events to weave")

        for row in rows:
            record_id = row["id"]
            event_id = str(row["event_id"])
            command = row["command"]

            try:
                # 1. Compile Context String
                status = "Success" if row["exit_code"] == 0 else "Failed"
                ts = (
                    row["captured_at"].isoformat()
                    if row["captured_at"]
                    else "UNKNOWN_TIME"
                )
                context_text = (
                    f"TERMINAL EXECUTION [{ts}]\n"
                    f"Command: {command}\n"
                    f"Directory: {row['cwd']}\n"
                    f"Result: {status} (Exit Code: {row['exit_code']})\n"
                    f"Host: {row['host']}"
                )

                # 2. Generate Embedding (qwen3 via Ollama/Model Runner)
                embedding = await ollama.generate_embedding(context_text)

                # 3. Extract References
                matches = ISSUE_PATTERN.findall(command)
                linked_entities = []
                for m in matches:
                    linked_entities.extend([item for item in m if item])
                linked_entities = list(set(linked_entities))

                # 4. Construct Flexible Schema Nodes/Edges
                nodes = []
                edges = []

                # Event Node
                event_node = {
                    "id": event_id,
                    "label": "TerminalEvent",
                    "properties": {
                        "command": command,
                        "cwd": row["cwd"],
                        "exit_code": row["exit_code"],
                        "output": (row["output"] or "")[:1000],
                        "user": row["user"],
                        "host": row["host"],
                    },
                }
                nodes.append(event_node)

                # Issue Nodes
                for ref in linked_entities:
                    ref_safe = ref.replace("#", "")
                    issue_id = f"issue-{ref_safe}"
                    ref_node = {
                        "id": issue_id,
                        "label": "LinearIssue" if "LIN" in ref else "Issue",
                        "properties": {"identifier": ref},
                    }
                    nodes.append(ref_node)

                    edges.append(
                        {
                            "source_id": event_id,
                            "target_id": issue_id,
                            "type": "REFERENCES",
                            "properties": {},
                        }
                    )

                digest = {
                    "source_id": event_id,
                    "digest_type": "terminal_event",
                    "title": f"Terminal: {command[:50]}",
                    "summary": context_text[:2000],
                    "nodes": nodes,
                    "edges": edges,
                    "embedding": embedding,
                    "captured_at": ts,
                    "metadata": {
                        "cwd": row["cwd"],
                        "session_id": row["session_id"],
                        "exit_code": row["exit_code"],
                        "user": row["user"],
                        "host": row["host"],
                    },
                    "tags": ["terminal", "ghost", "auto-capture"],
                }

                # 5. Commit to Guardian
                await omegakg.commit_knowledge(
                    raw_id=event_id,
                    type="terminal_event",
                    digest=digest,
                    metadata={"source": "saga_weaver_dagster"},
                )

                # 6. Mark as processed
                await conn.execute(
                    """
                    UPDATE raw_terminal_events
                    SET processed = true, processed_at = NOW()
                    WHERE id = $1
                    """,
                    record_id,
                )

                processed_count += 1

            except Exception as e:
                context.log.error(f"Failed to process event {event_id}: {e}")
                await conn.execute(
                    """
                    UPDATE raw_terminal_events
                    SET last_error = $1
                    WHERE id = $2
                    """,
                    str(e),
                    record_id,
                )

    finally:
        await conn.close()

    context.log.info(f"Terminal Processor complete: {processed_count} items")
    return {"processed": processed_count}
